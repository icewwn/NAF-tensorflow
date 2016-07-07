# Normalized Advantage Functions (NAF) in TensorFlow

TensorFlow implementation of [Continuous Deep q-Learning with Model-based Acceleration](http://arxiv.org/abs/1603.00748).


## Requirements

- Python 2.7
- [gym](https://github.com/openai/gym)
- [tqdm](https://github.com/tqdm/tqdm)
- [TensorFlow](https://www.tensorflow.org/)


## Usage

First, install prerequisites with:

    $ pip install tqdm gym[all]

To train a model for Breakout:

    $ python main.py --env=CartPole-v0 --is_train=True
    $ python main.py --env=CartPole-v0 --is_train=True --display=True

To test and record the screens with gym:

    $ python main.py --is_train=False
    $ python main.py --is_train=False --display=True


## Results

(in progress)


## Author

Taehoon Kim / [@carpedm20](http://carpedm20.github.io/)