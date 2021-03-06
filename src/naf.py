import gym
import numpy as np
from tqdm import tqdm
import tensorflow as tf

from .agent import Agent
from .memory import Memory
from .network import Network
from .utils import get_timestamp
from .statistic import Statistic

class NAF(Agent):
  def __init__(self,
               sess,
               model_dir,
               env_name,
               noise,
               noise_scale,
               discount=0.99,
               memory_size=100000,
               batch_size=32,
               learning_rate=1e-4,
               learn_start=10,
               max_step=10000,
               max_update=10000,
               max_episode=1000000,
               test_epoch=20,
               target_q_update_step=1000):
    self.sess = sess
    self.model_dir = model_dir
    self.env_name = env_name
    self.env = gym.make(env_name)
    self.action_size = self.env.action_space.shape[0]

    assert isinstance(self.env.observation_space, gym.spaces.Box), \
      "observation space must be continuous"
    assert isinstance(self.env.action_space, gym.spaces.Box), \
      "action space must be continuous"

    self.noise = noise
    self.noise_scale = noise_scale
    self.discount = discount
    self.max_step = max_step
    self.max_update = max_update
    self.max_episode = max_episode
    self.batch_size = memory_size
    self.learn_start = learn_start
    self.learning_rate = learning_rate
    self.target_q_update_step = target_q_update_step

    self.memory = Memory(self.env, batch_size, memory_size)

    self.pred_network = Network(
      session=sess,
      input_shape=self.env.observation_space.shape,
      action_size=self.env.action_space.shape[0],
      hidden_dims=[200, 200],
      name='pred_network',
    )
    self.target_network = Network(
      session=sess,
      input_shape=self.env.observation_space.shape,
      action_size=self.env.action_space.shape[0],
      hidden_dims=[200, 200],
      name='target_network',
    )
    self.target_network.make_copy_from(self.pred_network)

    self.stat = Statistic(sess, test_epoch, learn_start, model_dir, self.pred_network.variables)

  def train(self, monitor=False, display=False):
    self.optim = tf.train.AdamOptimizer(self.learning_rate) \
      .minimize(self.pred_network.loss, var_list=self.pred_network.variables)

    self.stat.load_model()

    if monitor:
      self.env.monitor.start('/tmp/%s-%s' % (self.env_name, get_timestamp()))

    self.target_network.update_from(self.pred_network)
    for self.idx_episode in tqdm(range(0, self.max_episode), ncols=70):
      state = self.env.reset()

      for t in xrange(0, self.max_step):
        if display: self.env.render()

        # 1. predict
        action = self.predict(state)
        # 2. step
        state, reward, terminal, _ = self.env.step(self.env.action_space.sample())
        # 3. perceive
        q, loss, is_update = self.perceive(state, reward, action, terminal)

        if self.stat and q != None and loss != None:
          self.stat.on_step(action, reward, terminal, q, loss, is_update)

        if terminal: break

    if mointor:
      self.env.monitor.close()

  def predict(self, state):
    u = self.pred_network.predict([state])[0]

    # from https://gym.openai.com/evaluations/eval_CzoNQdPSAm0J3ikTBSTCg
    # add exploration noise to the action
    if self.noise == 'linear_decay':
      action = u + np.random.randn(self.action_size) / (idx_episode + 1)
    elif self.noise == 'exp_decay':
      action = u + np.random.randn(self.action_size) * 10 ** -idx_episode
    elif self.noise == 'fixed':
      action = u + np.random.randn(self.action_size) * self.noise_scale
    elif self.noise == 'covariance':
      if self.action_size == 1:
        std = np.minimum(self.noise_scale / P(x)[0], 1)
        #print "std:", std
        action = np.random.normal(u, std, size=(1,))
      else:
        cov = np.minimum(np.linalg.inv(P(x)[0]) * self.noise_scale, 1)
        #print "covariance:", cov
        action = np.random.multivariate_normal(u, cov)
    else:
      assert False

    return action

  def perceive(self, state, reward, action, terminal):
    self.memory.add(state, reward, action, terminal)

    q, loss = None, None
    if self.memory.count > self.learn_start:
      q, loss = self.q_learning_minibatch()

    is_update = False
    if self.stat.t % self.target_q_update_step == self.target_q_update_step - 1:
      self.target_network.update_from(self.pred_network)
      is_update = True

    return q, loss, is_update

  def q_learning_minibatch(self):
    total_loss = 0.

    for iteration in xrange(self.max_update):
      x_t, u_t, r_t, x_t_plus_1, terminal = self.memory.sample()
      q_t_plus_1 = self.target_network.Q.eval({
        self.target_network.x: x_t,
        self.target_network.u: u_t,
        self.target_network.is_train: False,
      })

      terminal = np.array(terminal) + 0.
      max_q_t_plus_1 = np.max(q_t_plus_1, axis=1)
      target_q_t = (1. - terminal) * self.discount * max_q_t_plus_1 + r_t

      _, q_t, loss = self.sess.run(
        [self.optim, self.pred_network.Q, self.pred_network.loss], {
          self.pred_network.target_Q: target_q_t,
          self.pred_network.x: x_t,
          self.pred_network.u: u_t,
          self.pred_network.is_train: True,
        })

      total_loss += loss

    return q_t, loss
