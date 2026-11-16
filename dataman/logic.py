"""Business-logic layer.

Rules live here. This file never calls input() or print().
It reaches data only through a store object (see store.py).

"""
import re
from dataclasses import dataclass

MAX_ATTEMPTS = 2      # Two tries per problem.
MAX_SET_SIZE = 10     # Up to ten problems in the Memory Bank.
SCORE_EVERY = 10      # Score is shown after ten problems.
GUESS_LOW, GUESS_HIGH = 9, 100   # Secret is between 9 and 100.

_PROBLEM_RE = re.compile(r"^\s*(\d+)\s*([+\-x×*/÷])\s*(\d+)\s*=?\s*$", re.I)
_OPS = {"+": "+", "-": "-", "x": "x", "×": "x", "*": "x", "/": "÷", "÷": "÷"}


@dataclass(frozen=True)
class Problem:
    id: str
    prompt: str
    answer: int                 # for division: the whole-number part
    remainder: int | None = None  # division only


@dataclass(frozen=True)
class Outcome:
    """What the interface needs in order to draw a screen. Nothing more."""
    status: str                  # "correct" | "retry" | "reveal"
    try_number: int              # the try that was just used
    revealed_answer: int | None  # set only when status == "reveal"
    remainder: int | None = None  # set for division with a non-zero remainder


@dataclass(frozen=True)
class GuessOutcome:
    status: str     # "narrowed" | "won"
    tries_used: int
    low: int        # the secret is still somewhere from low to high (inclusive)
    high: int


class SetFull(Exception):
    """Raised when a Memory Bank set already holds MAX_SET_SIZE problems."""


class InvalidProblem(ValueError):
    """Raised when text is not a usable problem such as '6 x 6' or '12 / 5'."""


class AttemptsExhausted(Exception):
    """Raised when a session is already finished and gets another answer."""


class GameOver(Exception):
    """Raised when a guess is submitted to a finished guessing game."""


class OutOfRange(ValueError):
    """Raised for a guess outside GUESS_LOW..GUESS_HIGH. It does not use a try."""


def parse_problem(text: str) -> Problem:
    """'2+7', '6 X 6 =', '12 / 5' -> Problem. Operators: + - x (or *) and / (or ÷)."""
    m = _PROBLEM_RE.match(text)
    if not m:
        raise InvalidProblem("Please type a problem like 6 x 6, 7 + 6 or 12 / 5.")
    a, op, b = int(m[1]), _OPS[m[2].lower()], int(m[3])
    prompt = f"{a} {op} {b}"
    if op == "+":
        return Problem(prompt, prompt, a + b)
    if op == "-":
        return Problem(prompt, prompt, a - b)
    if op == "x":
        return Problem(prompt, prompt, a * b)
    if b == 0:
        raise InvalidProblem("We cannot divide by zero. Try a different number.")
    quotient, remainder = divmod(a, b)
    return Problem(prompt, prompt, quotient, remainder)


# ---------------------------------------------------------------- answer checker
class PracticeSession:
    """One learner, one try-pair at one problem. State comes from the store."""

    def __init__(self, store, session_id: str, problem: Problem):
        self.store = store
        self.session_id = session_id
        self.problem = problem

    def attempts(self) -> list[dict]:
        return self.store.attempts_for(self.session_id, self.problem.id)

    def is_finished(self) -> bool:
        rows = self.attempts()
        return bool(rows) and (rows[-1]["correct"] or len(rows) >= MAX_ATTEMPTS)

    def next_try(self) -> int:
        return len(self.attempts()) + 1

    def submit(self, answer: int) -> Outcome:
        if self.is_finished():
            raise AttemptsExhausted(self.problem.id)
        try_number = self.next_try()
        correct = answer == self.problem.answer
        self.store.save_attempt(
            self.session_id, self.problem.id, try_number, answer, correct
        )
        remainder = self.problem.remainder or None
        if correct:
            return Outcome("correct", try_number, None, remainder)
        if try_number >= MAX_ATTEMPTS:
            return Outcome("reveal", try_number, self.problem.answer, remainder)
        return Outcome("retry", try_number, None)


def result_label(attempts: list[dict]) -> str:
    """Curator view: tell the three outcomes apart."""
    if not attempts:
        return "not attempted"
    if attempts[0]["correct"]:
        return "first-try success"
    if len(attempts) >= 2 and attempts[1]["correct"]:
        return "second-try success"
    if len(attempts) >= MAX_ATTEMPTS:
        return "two misses"
    return "in progress"


def next_round_id(store, player_id: str) -> str:
    """Each problem played is one round, so the same problem can be played twice."""
    return f"{player_id}:{len(rounds_for(store, player_id)) + 1}"


def rounds_for(store, player_id: str) -> list[dict]:
    rounds: dict[str, dict] = {}
    for a in store.attempts_for_player(player_id):
        rounds.setdefault(a["session_id"], {"problem": a["problem_id"], "attempts": []})
        rounds[a["session_id"]]["attempts"].append(a)
    return list(rounds.values())


def curator_report(store, player_id: str) -> list[dict]:
    """Curator view: every round with its outcome label and every attempt."""
    return [{"problem": r["problem"], "label": result_label(r["attempts"]),
             "attempts": r["attempts"]} for r in rounds_for(store, player_id)]


def finished_count(store, player_id: str) -> int:
    return sum(1 for r in curator_report(store, player_id) if r["label"] != "in progress")


def score_last(store, player_id: str, n: int = SCORE_EVERY) -> tuple[int, int]:
    """(right, tried) over the last n finished problems. Right = solved within two tries."""
    done = [r for r in curator_report(store, player_id) if r["label"] != "in progress"][-n:]
    right = sum(1 for r in done if r["label"].endswith("success"))
    return right, len(done)


# ------------------------------------------------------------------ memory bank
class MemoryBank:
    """A practice set of problems. The size limit is a business rule."""

    def __init__(self, store, set_id: str):
        self.store = store
        self.set_id = set_id

    def members(self) -> list[str]:
        return self.store.members(self.set_id)

    def problems(self) -> list[Problem]:
        return [parse_problem(m) for m in self.members()]

    def add_problem(self, text: str) -> bool:
        """Return True if added, False if it was already in the set."""
        prompt = parse_problem(text).prompt   # raises InvalidProblem
        current = self.members()
        if prompt in current:
            return False
        if len(current) >= MAX_SET_SIZE:
            raise SetFull(f"The Memory Bank is full. It holds up to {MAX_SET_SIZE} problems.")
        self.store.add_member(self.set_id, prompt)
        return True


# ---------------------------------------------------------------- number guesser
def new_secret(rng) -> int:
    """rng is any object with randint (e.g. random.Random(1)), so tests can seed it."""
    return rng.randint(GUESS_LOW, GUESS_HIGH)


class GuessGame:
    """One game, no try limit (as in the manual). In-progress state lives here;
    only the finished result is written to the store."""

    def __init__(self, store, player_id: str, secret: int):
        if not GUESS_LOW <= secret <= GUESS_HIGH:
            raise OutOfRange(secret)
        self.store = store
        self.player_id = player_id
        self._secret = secret
        self.tries = 0
        self.low, self.high = GUESS_LOW, GUESS_HIGH
        self._finished = False

    def is_finished(self) -> bool:
        return self._finished

    def guess(self, value: int) -> GuessOutcome:
        if self._finished:
            raise GameOver()
        if not GUESS_LOW <= value <= GUESS_HIGH:
            raise OutOfRange(value)
        self.tries += 1
        if value == self._secret:
            self._finished = True
            self.store.save_game(self.player_id, True, self.tries)
            return GuessOutcome("won", self.tries, value, value)
        if value < self._secret:
            self.low = max(self.low, value + 1)
        else:
            self.high = min(self.high, value - 1)
        return GuessOutcome("narrowed", self.tries, self.low, self.high)


def guesser_report(store, player_id: str) -> dict:
    games = store.games_for(player_id)
    wins = [g["tries"] for g in games if g["won"]]
    return {"played": len(games), "won": len(wins),
            "best": min(wins) if wins else None}
