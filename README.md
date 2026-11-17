# Dataman - Text-Only Prototype

## Project Description
DataMan is a text-based math practice program. It allows learners to answer math problems, receive feedback, and save problems to practice again.

## Features
- Answer Checker with two attempts per problem. 
- Feedback for correct and incorrect answers.
- Displays the correct answer after two missed attempts.
- Memory Bank stores up to 10 math problems.
- Tracks scores and accuracy.
- Supports temporary and JSON file storage.

## Project Files 
- app.py – Handles menus, user input, and messages.
- dataman/logic.py – Contains the math rules, answer checking, and scoring.
- dataman/store.py – Saves and retrieves attempts and saved problems.
- dataman_store.json – Stores data when using JSON storage.

## How to Run
Run Program
   `python app.py`

## Design and Testing
The project uses three separate layers:
1. Text Interface: Handles user input and displays results.
2. Business Logic: Controls the two-attempt rule, problem validation, and scoring.
3. Data Layer: Stores practice attempts and Memory Bank problems.
The two-attempt rule can be tested by entering a math problem and submitting incorrect and correct answers.

## Limitations
- Uses a placeholder learner ID instead of user accounts.
- Uses a text interface instead of a Flask web application.
- JSON storage does not include advanced error recovery or database features.
