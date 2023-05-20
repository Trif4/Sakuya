from pathlib import Path


with Path(__file__).with_name('word_list.txt').open('r') as f:
    WORD_LIST = f.read().splitlines()

with Path(__file__).with_name('valid_guesses.txt').open('r') as f:
    VALID_GUESSES = set(f.read().splitlines()) | set(WORD_LIST)

with Path(__file__).with_name('letter_emotes.txt').open('r') as f:
    LETTER_EMOTES = f.read().splitlines()
