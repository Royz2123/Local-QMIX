import math
import gym
from gym import spaces, logger
from gym.utils import seeding
import numpy as np
from gym.envs.classic_control import rendering

import random

import envs.multi_cart.constants as constants


class SingleCart(object):
    """
    Description:
        A pole is attached by an un-actuated joint to a cart, which moves along
        a frictionless track. The pendulum starts upright, and the goal is to
        prevent it from falling over by increasing and reducing the cart's
        velocity.
    Source:
        This environment corresponds to the version of the cart-pole problem
        described by Barto, Sutton, and Anderson
    Observation:
        Type: Box(4)
        Num     Observation               Min                     Max
        0       Cart Position             -4.8                    4.8
        1       Cart Velocity             -Inf                    Inf
        2       Pole Angle                -0.418 rad (-24 deg)    0.418 rad (24 deg)
        3       Pole Angular Velocity     -Inf                    Inf
    Actions:
        Type: Discrete(2)
        Num   Action
        0     Push cart to the left
        1     Push cart to the right
        Note: The amount the velocity that is reduced or increased is not
        fixed; it depends on the angle the pole is pointing. This is because
        the center of gravity of the pole increases the amount of energy needed
        to move the cart underneath it
    Reward:
        Reward is 1 for every step taken, including the termination step
    Starting State:
        All observations are assigned a uniform random value in [-0.05..0.05]
    Episode Termination:
        Pole Angle is more than 12 degrees.
        Cart Position is more than 2.4 (center of the cart reaches the edge of
        the display).
        Episode length is greater than 200.
        Solved Requirements:
        Considered solved when the average return is greater than or equal to
        195.0 over 100 consecutive trials.
    """

    def __init__(self, params, offset=0):
        self.seed()

        self.viewer = None
        self.state = None
        self.steps_beyond_done = None

        self.offset = offset
        self.params = params

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, action, left_pos=None, right_pos=None):
        x, x_dot, theta, theta_dot = self.state

        # calculate spring force
        total_spring_force = 0
        if self.params["coupled"]["mode"]:
            for i, cart_pos in enumerate([left_pos, right_pos]):
                if cart_pos is not None:
                    sign = 1 if i == 0 else -1
                    total_spring_force += self.params["coupled"]["spring_k"] * (
                        cart_pos - x + sign * self.params["coupled"]["resting_dist"]
                    )

        # print(f"stats\n\n\n")
        # print(left_pos)
        # print(right_pos)
        # print(total_spring_force)

        force = self.params["physics"]["force_mag"] if action == 1 else -self.params["physics"]["force_mag"]
        if self.params["test_physics"]:
            force = 0
        force += total_spring_force

        costheta = math.cos(theta)
        sintheta = math.sin(theta)

        # For the interested reader:
        # https://coneural.org/florian/papers/05_cart_pole.pdf
        temp = (force + self.params["physics"]["polemass_length"] * theta_dot ** 2 * sintheta) / self.params["physics"]["total_mass"]
        thetaacc = (constants.GRAVITY * sintheta - costheta * temp) / (
                    self.params["physics"]["length"] * (4.0 / 3.0 - self.params["physics"]["masspole"] * costheta ** 2 / self.params["physics"]["total_mass"]))
        xacc = temp - self.params["physics"]["polemass_length"] * thetaacc * costheta / self.params["physics"]["total_mass"]

        if self.params["physics"]["kinematics_integrator"] == 'euler':
            x = x + self.params["physics"]["tau"] * x_dot
            x_dot = x_dot + self.params["physics"]["tau"] * xacc
            theta = theta + self.params["physics"]["tau"] * theta_dot
            theta_dot = theta_dot + self.params["physics"]["tau"] * thetaacc
        else:  # semi-implicit euler
            x_dot = x_dot + self.params["physics"]["tau"] * xacc
            x = x + self.params["physics"]["tau"] * x_dot
            theta_dot = theta_dot + self.params["physics"]["tau"] * thetaacc
            theta = theta + self.params["physics"]["tau"] * theta_dot

        self.state = (x, x_dot, theta, theta_dot)

    def reset(self):
        self.state = self.np_random.uniform(low=-0.05, high=0.05, size=(4,))
        self.state[0] += self.offset

    def is_done(self):
        x, x_dot, theta, theta_dot = self.state

        valid_pole = (
            self.params["test_physics"]
            or bool(
                theta >= -constants.THETA_THRESHOLD_RADIANS
                and theta <= constants.THETA_THRESHOLD_RADIANS
            )
        )
        done = bool(
            x < self.params["bottom_threshold"]
            or x > self.params["top_threshold"]
            or not valid_pole
        )

        return done

    def render(self, viewer, init=False, mode='human'):
        if init:
            # line background
            self.track = rendering.Line(
                (0, self.params["screen"]["carty"]),
                (self.params["screen"]["width"], self.params["screen"]["carty"])
            )
            self.track.set_color(0, 0, 0)
            viewer.add_geom(self.track)

            # cart
            l, r = -self.params["screen"]["cartwidth"] / 2, self.params["screen"]["cartwidth"] / 2
            t, b = self.params["screen"]["cartheight"] / 2, -self.params["screen"]["cartheight"] / 2
            axleoffset = self.params["screen"]["cartheight"] / 4.0
            cart = rendering.FilledPolygon([(l, b), (l, t), (r, t), (r, b)])

            # set cart color
            random.seed(self.offset)
            cart_color = random.random() / 2.0
            cart.set_color(cart_color, cart_color, cart_color)

            self.carttrans = rendering.Transform()
            cart.add_attr(self.carttrans)
            viewer.add_geom(cart)

            l, r = -self.params["screen"]["polewidth"] / 2, self.params["screen"]["polewidth"] / 2
            t = self.params["screen"]["polelen"] - self.params["screen"]["polewidth"] / 2
            b = -self.params["screen"]["polewidth"] / 2

            pole = rendering.FilledPolygon([(l, b), (l, t), (r, t), (r, b)])
            pole.set_color(.8, .6, .4)
            self.poletrans = rendering.Transform(translation=(0, axleoffset))
            pole.add_attr(self.poletrans)
            pole.add_attr(self.carttrans)
            viewer.add_geom(pole)

            self.axle = rendering.make_circle(self.params["screen"]["polewidth"] / 2)
            self.axle.add_attr(self.poletrans)
            self.axle.add_attr(self.carttrans)
            self.axle.set_color(.5, .5, .8)
            viewer.add_geom(self.axle)

            self._pole_geom = pole

        if self.state is None:
            return None

        # Edit the pole polygon vertex
        pole = self._pole_geom
        l, r, t, b = -self.params["screen"]["polewidth"] / 2, self.params["screen"]["polewidth"] / 2, self.params["screen"]["polelen"] - self.params["screen"]["polewidth"] / 2, -self.params["screen"]["polewidth"] / 2
        pole.v = [(l, b), (l, t), (r, t), (r, b)]

        x = self.state

        # normalize for display
        cartx = x[0] * self.params["scale"]
        cartx += abs(self.params["bottom_threshold"]) * self.params["scale"]

        self.carttrans.set_translation(cartx, self.params["screen"]["carty"])
        self.poletrans.set_rotation(-x[2])

    def close(self):
        if self.viewer:
            self.viewer.close()
            self.viewer = None
