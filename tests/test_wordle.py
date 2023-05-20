import pytest

from sakuya.wordle.guess import GuessLengthError, parse_guess


@pytest.mark.parametrize('guess,expected', [
    ('shark', 'shark'),  # string guess
    ('🦈', 'shark'),  # emoji
    ('<:AYAYA:618951000916754432>', 'ayaya'),  # Discord emote
    ('🤡', 'clown'),  # multiword emoji
    ('🤸‍♀️', 'woman'),  # emoji sequence
    ('👨‍⚖️', 'judge'),  # emoji sequence
    ('🍳', 'fried'),  # alias + multiword
    ('s🐑r', 'sewer'),  # emoji combined with letters
    ('🅰️Y🅰️Y🅰️', 'ayaya'),  # multiple emoji combined with letters
    ('<:a_grey:931614253394309120>YAY<:a_grey:931614253394309120>', 'ayaya'),  # multiple Discord emotes
    ('🐟<:y_grey:931613702199857243>', 'fishy'),  # emoji + Discord emote
    ('<:lawnmower:927011154868449350>', 'mower'),  # compound word
    ('<:AYAYAWeird:807004237573390428>', 'weird'),  # compound word
    ('s<:tetriuTea:828458481857593344>m', 'steam'),  # compound word with hinted separation that wordninja fails on
    ('<:trifAYAYA:713868338891194398>', 'ayaya'),  # compound word with all capital letters at the end
    ('👩‍✈️', 'pilot'),  # two valid words
    ('👍', 'thumb'),  # plural -> singular
    ('<:ThumbsUp:123123124>', 'thumb'),  # also works for Discord emotes
    ('thumbs', None),  # string guesses are not modified
    ('👡', 'woman'),  # no apostrophe
    ('👍🏻', 'thumb'),  # skin tone is less important than main word
    ('<:🅰️Y🅰️Y🅰️:12345>', None)  # illegal
])
def test_parse_guess(guess, expected):
    if expected:
        assert parse_guess(guess) == expected
    else:
        with pytest.raises(GuessLengthError):
            parse_guess(guess)
