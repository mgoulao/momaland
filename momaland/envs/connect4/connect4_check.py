"""MO Connect4 check."""

import numpy as np
from connect4 import MOConnect4


def main():
    """Checks the environment."""
    environment = MOConnect4(board_width=7, board_height=6, column_objectives=False)
    environment.reset(seed=42)

    for agent in environment.agent_iter():
        action = environment.action_space(agent).seed(42)
        observation, reward, termination, truncation, info = environment.last()

        print("rewards", environment.rewards)
        if termination or truncation:
            action = None
        else:
            if observation:
                mask = observation["action_mask"]
                # this is where you would insert your policy
                action = environment.action_space(agent).sample(mask)
                print("observation: ", observation)
                # print("cumulative rewards", environment._cumulative_rewards)
                # print("action: ", action)

        environment.step(action)

    # print("observation: ", observation)
    print("reward: ", reward)
    print("rewards", environment.rewards)
    # print("cumulative rewards", environment._cumulative_rewards)
    # name = input("Press key to end\n")
    environment.close()


def random_test():
    """Checks restoring rng state."""
    rng = np.random.default_rng()
    st0 = rng.__getstate__()
    print(rng.integers(low=0, high=10, size=5))
    print(rng.integers(low=0, high=10, size=10))
    rng.__setstate__(st0)
    print(rng.integers(low=0, high=10, size=5))


if __name__ == "__main__":
    random_test()
