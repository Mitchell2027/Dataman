"""Text interface layer. This is the only file that uses input() and print().

Run from the project root:
    python app.py                 (data lives in RAM)
    python app.py --store json    (data survives a restart, in dataman_store.json)
"""
import argparse
import random
import time

from dataman.logic import (GUESS_HIGH, GUESS_LOW, MAX_SET_SIZE, SCORE_EVERY,
                           GuessGame, InvalidProblem, MemoryBank, OutOfRange,
                           PracticeSession, SetFull, curator_report,
                           finished_count, guesser_report, new_secret,
                           next_round_id, parse_problem, score_last)
from dataman.store import JsonFileStore, MemoryStore

SESSION = "player-1" # STUB: one learner until there is a login.
RNG = random.Random()

MENU = """
======= DATAMAN MENU ========
1) Play Answer Checker
2) Play Memory Bank
3) Play Number guesser
4) Report
5) Exit"""


def parse_int(raw):
    """Return an int, or None if raw is not a whole number."""
    # Validate user input
    try:
        return int(raw.strip()) # Remove extra spaces
    except ValueError:
        return None

# Calculate and display performance
def show_score(store, n=SCORE_EVERY, seconds=None):
    # retrieves the number of correct answers and attempts
    right, tried = score_last(store, SESSION, n)
    extra = f", in {seconds} seconds" if seconds is not None else ""
    print(f"Score: {right} of {tried} right{extra}.")

# Two tries handling, 
def play_round(store, problem):
    """Two tries at one problem. Returns the final Outcome."""
    # Creates an new practice session
    session = PracticeSession(store, next_round_id(store, SESSION), problem)
    out = None
    while not session.is_finished():
        value = parse_int(input(f"Try {session.next_try()}: {problem.prompt} = "))
        if value is None:
            print("Please type a whole number, like 12.")
            continue
        out = session.submit(value)
        rem = f" Remainder: {out.remainder}." if out.remainder else ""
        if out.status == "correct":
            print(f"Correct! Great job.{rem}")
        elif out.status == "retry":
            print("Oops, that answer is wrong. Give it another try!")
        else:
            print(f"Not this time. The answer is {out.revealed_answer}.{rem}")
    return out


# Answer Checker Game
def practice(store):
    while True:
        print("\n------- ANSWER CHECKER -------")
        print("1. Enter a problem")
        print("2. Stop Session")
        choice = input("Choose an option: ").strip()
        if choice == "2":
            print("Practice session ended.")
            return
        if choice != "1":
            print("Please choose 1 or 2.")
            continue
        text = input("Enter a problem (ex: 6 x 6 or 12 / 5): ") 
        try:
            problem = parse_problem(text)
        except InvalidProblem as err:
            print(err)
            continue
        play_round(store, problem)
        if finished_count(store, SESSION) % SCORE_EVERY == 0:
            show_score(store)

# Memory Bank Game
def fill_bank(memory_bank):
    """Keep asking for problems until the bank is full (10) or the player stops."""
    while len(memory_bank.members()) < MAX_SET_SIZE:
        n = len(memory_bank.members()) + 1
        text = input(f"\nEnter problem {n} of {MAX_SET_SIZE} (type S to stop): ").strip()
        if text.lower() == "s":
            print("Finished adding problems.")
            return
        if not text:
            print("Please enter a math problem.")
            continue
        try:
            if memory_bank.add_problem(text):
                print("Stored.")
            else:
                print("That problem is already stored. Try a different one.")
        except InvalidProblem as err:
            print(f"Oops! {err}")
    print(f"The Memory Bank is full!")

# Memory Bank menu
def bank(store):
    """Memory Bank menu."""
    memory_bank = MemoryBank(store, "set-1")
    if not memory_bank.members():
        print("\nWelcome to Memory Bank!")
        print("You can save up to 10 math problems.")
        fill_bank(memory_bank)
    while True:
        print("\n---------- MEMORY BANK -----------")
        print("1. Add Problems")
        print("2. Practice Saved Problems")
        print("3. View Score")
        print("4. Back to Main Menu")
        choice = input("\nChoose an option: ").strip()
        if choice == "1":
            fill_bank(memory_bank)
        elif choice == "2":
            held = memory_bank.members()
            if not held:
                print("\nYour Memory Bank is empty.")
                continue
            print("\nStarting Memory Bank practice!")
            print("Press ENTER for a random problem.")
            print("Type S to stop practicing.")
            while True:
                command = input(
                    "\nPress ENTER for a problem or type S to stop: "
                ).strip()
                if command.lower() == "s":
                    print("Practice session ended.")
                    break
                if command:
                    print("Press ENTER for a problem or S to stop.")
                    continue
                problem_text = RNG.choice(held)
                try:
                    problem = parse_problem(problem_text)
                    play_round(store, problem)
                except InvalidProblem as err:
                    print(f"Invalid saved problem: {err}")
        elif choice == "3":
            correct, total = score_last(store, SESSION) 
            if total == 0:
                print("\nNo completed problems yet.")
            else:
                accuracy = (correct / total) * 100
                print("\n===== MEMORY BANK SCORE =====")
                print(f"Correct: {correct}")
                print(f"Total: {total}")
                print(f"Accuracy: {accuracy:.1f}%")

        elif choice == "4":
            print("Returning to the main menu.")
            break

        else:
            print("Invalid choice. Please select 1-4.")
# Number Guesser
def guesser(store):
    print("\n------ Welcome to Number Guesser --------")
    game = GuessGame(store, SESSION, new_secret(RNG))
    print(f"I picked a secret number from {GUESS_LOW} to {GUESS_HIGH}. (q to give up)")
    while not game.is_finished():
        raw = input("Your guess: ")
        if raw.strip().lower() == "q":
            print("Okay, game stopped. It will not be counted.")
            return
        value = parse_int(raw)
        if value is None:
            print("Please type a whole number, like 12.")
            continue
        try:
            out = game.guess(value)
        except OutOfRange:
            print(f"Try a number from {GUESS_LOW} to {GUESS_HIGH}. That one did not use up a try.")
            continue
        if out.status == "won":
            print(f"You got it in {out.tries_used} {'try' if out.tries_used == 1 else 'tries'}!")
        else:
            print(f"The secret number is between {out.low} and {out.high}.")

# Report Option
def report(store):
    print(f"\nAnswer checker for {SESSION}:")
    rounds = curator_report(store, SESSION)
    if not rounds:
        print("  not attempted")
    for r in rounds:
        print(f"  {r['problem']}: {r['label']}")
        for a in r["attempts"]:
            print(f"    try {a['try']}: answered {a['answer']} -> "
                  f"{'correct' if a['correct'] else 'wrong'}")
    if rounds:
        right, tried = score_last(store, SESSION)
        print(f"  Latest score: {right} of {tried} right")
    g = guesser_report(store, SESSION)
    best = f", best win in {g['best']} tries" if g["best"] else ""
    print(f"Number guesser: won {g['won']} of {g['played']}{best}")
    print(f"Memory bank set-1: {len(MemoryBank(store, 'set-1').members())} of {MAX_SET_SIZE} problems")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", choices=["memory", "json"], default="memory")
    args = parser.parse_args(argv)
    store = JsonFileStore() if args.store == "json" else MemoryStore()
    actions = {"1": practice, "2": bank, "3": guesser, "4": report}
    try:
        while True:
            print(MENU)
            print("")
            choice = input("Choose 1-5 > ").strip()
            if choice == "5":
                break
            if choice in actions:
                actions[choice](store)
            else:
                print("Please type a number from 1 to 5.")
    except (EOFError, KeyboardInterrupt):
        print()
    print("Thanks For Playing.")


if __name__ == "__main__":
    main()
