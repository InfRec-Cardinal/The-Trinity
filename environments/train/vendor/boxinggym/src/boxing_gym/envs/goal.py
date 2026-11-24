class Goal:
    def __init__(self, env):
        self.env = env
    
    def get_system_message(self, include_prior):
        raise NotImplementedError
    
    def get_goal_eval_question(self, include_prior):
        raise NotImplementedError

    def evaluate_predictions(self, predictions, measurements):
        raise NotImplementedError