from abc import ABC, abstractmethod


class Codemaster(ABC):
    pass                                                                           

    def __init__(self):
        pass                                                
        self.move_history = []
        pass

    def set_move_history(self, move_history):
        pass                                                                    
        self.move_history = move_history

    def get_move_history(self):
        pass                                           
        return self.move_history

    @abstractmethod
    def set_game_state(self, words_on_board, key_grid):
        pass                                             
        pass

    @abstractmethod
    def get_clue(self):
        pass                                                                                      
        pass


class HumanCodemaster(Codemaster):

    def __init__(self):
        super().__init__()
        self.team = team
        pass

    def set_game_state(self, words_in_play, map_in_play):
        self.words = words_in_play
        self.maps = map_in_play

    def get_clue(self):
        clue_input = input("Input CM Clue:\nPlease enter a Word followed by a space and a Number >> ")
        clue_input = clue_input.strip()
        type(clue_input)
        clue = clue_input.split(" ")

        if len(temp_clue) == 1:
            clue = [temp_clue[0],1]
        else:
            clue = [temp_clue[0], int(temp_clue[1])]
        return clue
