"""Wrappers for training.

Parallel only.

TODO AEC.
"""

import os
from typing import List, Tuple

import chex
import jax
import jax.numpy as jnp
import numpy as np
import pandas as pd
from distrax import MultivariateNormalDiag


def _ma_get_pi(actor_module, params, obs: jnp.ndarray, num_agents):
    """Gets the actions for all agents at once. This is done with a for loop because distrax does not like vmapping.

    Args:
        actor_module: actor module.
        params: actor state parameters.
        obs: current step environment observation.
        num_agents (int): number of agents in environments.

    Returns:
        pi.
    """
    return [actor_module.apply(params, obs[i]) for i in range(num_agents)]


def _ma_sample_and_log_prob_from_pi(pi: List[MultivariateNormalDiag], num_agents: int, key: chex.PRNGKey):
    """Samples actions for all agents in all the envs at once. This is done with a for loop because distrax does not like vmapping.

    Args:
        pi (List[MultivariateNormalDiag]): List of distrax distributions for agent actions (batched over envs).
        num_agents (int): number of agents in environments.
        key (chex.PRNGKey): PRNGKey to use for sampling: size should be (num_agents, 2).
    """
    return [pi[i].sample_and_log_prob(seed=key[i]) for i in range(num_agents)]


def eval_mo(actor_module, actor_state, env, num_obj, gamma_decay=0.99) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """Evaluates one episode of the agent in the environment.

    Args:
        actor_module: the initialized actor module
        actor_state: Agent
        env: MOMAland environment with LinearReward wrapper
        (np.ndarray): number of objectives

    Returns:
        (np.ndarray, np.ndarray): vectorized return, vectorized discounted return
    """
    key = jax.random.PRNGKey(seed=42)
    key, subkey = jax.random.split(key)
    obs, _ = env.reset()
    np_obs = np.stack([obs[agent] for agent in env.possible_agents])
    done = False
    vec_return, disc_vec_return = np.zeros_like(num_obj), np.zeros_like(num_obj)
    gamma = 1.0
    action_keys = jax.random.split(subkey, len(env.possible_agents))
    while not done:
        pi = _ma_get_pi(actor_module, actor_state.params, jnp.array(np_obs), len(env.possible_agents))
        # for each agent sample an action
        actions, _ = zip(*_ma_sample_and_log_prob_from_pi(pi, len(env.possible_agents), action_keys))
        actions_dict = dict()
        for i, agent in enumerate(env.possible_agents):
            actions_dict[agent] = np.array(actions[i])
        obs, rew, term, trunc, _ = env.step(actions_dict)
        done = term or trunc

        vec_return = np.array(list(rew.values())).sum(axis=0)
        disc_vec_return = gamma * vec_return
        gamma *= gamma_decay

    return (
        vec_return,
        disc_vec_return,
    )


def policy_evaluation_mo(
    actor_module, actor_state, env, num_obj: np.ndarray, rep: int = 5
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """Evaluates the value of a policy by running the policy for multiple episodes. Returns the average returns.

    Args:
        actor_module: the initialized actor module
        actor_state: Agent
        env: MOMAland environment
        num_obj (np.ndarray): number of objectives
        rep (int, optional): Number of episodes for averaging. Defaults to 5.

    Returns:
        (float, float, np.ndarray, np.ndarray): Avg scalarized return, Avg scalarized discounted return, Avg vectorized return, Avg vectorized discounted return
    """
    evals = [eval_mo(actor_module, actor_state, env, num_obj) for _ in range(rep)]
    avg_vec_return = np.mean([eval[0] for eval in evals], axis=0)
    avg_disc_vec_return = np.mean([eval[1] for eval in evals], axis=0)

    return (
        avg_vec_return,
        avg_disc_vec_return,
    )


def save_results(returns, exp_name, seed):
    """Saves the results of an experiment to a csv file.

    Args:
        returns: a list of triples (timesteps, time, episodic_return)
        exp_name: experiment name
        seed: seed of the experiment
    """
    if not os.path.exists("results"):
        os.makedirs("results")
    filename = f"results/{exp_name}_{seed}.csv"
    print(f"Saving results to {filename}")
    df = pd.DataFrame(returns)
    df.columns = ["Total timesteps", "Time", "Episodic return"]
    df.to_csv(filename, index=False)
