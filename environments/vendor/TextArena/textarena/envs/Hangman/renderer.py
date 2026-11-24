from typing import Dict, Any


def create_board_str(game_state: Dict[str, Any]) -> str:
    pass                                                                                                       
                                                                 
    hangman_stages = [
        [
            "  _______     ",
            " |/      |    ",
            " |      (X)   ",
            " |      /|\   ",
            " |      / \   ",
            " |            ",
            "_|___         "
        ],
        [
            "  _______     ",
            " |/      |    ",
            " |      (X)   ",
            " |      /|\   ",
            " |      /     ",
            " |            ",
            "_|___         "
        ],
        [
            "  _______     ",
            " |/      |    ",
            " |      (X)   ",
            " |      /|\   ",
            " |            ",
            " |            ",
            "_|___         "
        ],
        [
            "  _______     ",
            " |/      |    ",
            " |      (X)   ",
            " |      /|    ",
            " |            ",
            " |            ",
            "_|___         "
        ],
        [
            "  _______     ",
            " |/      |    ",
            " |      (X)   ",
            " |       |    ",
            " |            ",
            " |            ",
            "_|___         "
        ],
        [
            "  _______     ",
            " |/      |    ",
            " |      (X)   ",
            " |            ",
            " |            ",
            " |            ",
            "_|___         "
        ],
        [
            "  _______     ",
            " |/      |    ",
            " |            ",
            " |            ",
            " |            ",
            " |            ",
            "_|___         "
        ],
    ]

    hangman_drawing = hangman_stages[::-1][max(0, min(6, 6 - game_state['tries_left']))]

    return (
        f"🎯 Word: {game_state['target_word']}\n\n" +
        "\n".join(hangman_drawing) +
        f"\n\n❤️ Tries left: {game_state['tries_left']}"
    )