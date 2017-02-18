from __future__ import division
import numpy as np
from numpy import matrix
from numpy import linalg
import pickle
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.rcParams['font.family'] = 'serif'
label_size = 16
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 
from numpy import genfromtxt
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern
from astropy.visualization import hist
import os

import spike_n_slab

class Testing(object):


    """
    Class for doing various tests with the spike and slab, and Gaussian models
    on a toy dataset. In particular which of the models is better for different
    numbers of data points. 
    """

    
    def __init__(self, sizes, dim, runs, gen_weights = True):


        """
        Initialise some variables. 

        :type sizes: array of integers
        :param sizes: number of data points to generate for testing errors/
        generating weights.

        :type dim: integer
        :param sizes: number of features

        :type dim: integer
        :param sizes: number of features (relevant features is 2 always)

        :type runs: integer
        :param sizes: number of times to repeat test for each size (i.e. each
        number of data points), in order to get a less more accurate idea of
        the true error at that size. 

        :type gen_weigths: bool
        :param sizes: If true new data points and weights are generated by
        Gibbs sampling. If false then load old weights. Haven't yet implemented
        way to store data points, only weights associated with them. But the
        training data isn't needed to calculate errors. 
        """
        
        
        self.sizes = sizes
        self.dim = dim
        self.multi_dim = 4
        self.runs = runs
        self.gen_weights = gen_weights
        self.X_train, self.y_train, self.X_test, self.y_test = self.get_data()
        self.number_sizes = len(self.sizes)
        # arrays to put in individual guesses for weights
        # mle: Maximum likelihodd estimate
        # sns: Spike and slab prior
        # gauss: Gaussian prior
        self.mle_out = np.zeros(self.number_sizes)
        self.sns_out = np.zeros(self.number_sizes)
        self.gauss_out = np.zeros(self.number_sizes)
        # arrays to store several runs worth of weights
        self.big_mle_out = np.zeros([self.number_sizes, runs])
        self.big_sns_out = np.zeros([self.number_sizes, runs])
        self.big_gauss_out = np.zeros([self.number_sizes, runs])
        # arrays to store the mean of several runs
        self.mean_mle_out = np.zeros(self.number_sizes)
        self.mean_sns_out = np.zeros(self.number_sizes)
        self.mean_gauss_out = np.zeros(self.number_sizes)

    def get_data(self, size = 3):

        """
        Generate random test and training data

        :type size: integer
        :param size: Number of data points. Number of ouputs is four times this
        as each data point corresponds to four different target values
        """
        
        test_size = 200
        d = self.dim

        X = np.zeros([size, d])
        X_test = np.zeros([test_size, d])
        for i in range(d):
            X[:, i] = np.random.uniform(size = size)
            X_test[:, i] = np.random.uniform(size = test_size)
        # normalise test and train data
        for i in range(d):
            if np.std(X[:, i]) !=0:
                X[:, i] = (X[:, i] - np.mean(X[:, i]))/np.std(X[:, i])
                X_test[:, i] = (X_test[:, i] -
                            np.mean(X_test[:, i]))/np.std(X_test[:, i])
                
        Y_0 = (0.1*X[:, 1] + 0.1*X[:, 4] +
           np.random.normal(scale = 0.01, size = size))
        Y_1 = (0.3*X[:, 1] - 0.1*X[:, 4] +
           np.random.normal(scale = 0.01, size = size))
        Y_2 = (-0.5*X[:, 1] - 0.5*X[:, 4] +
           np.random.normal(scale = 0.01, size = size))
        Y_3 = (0.2*X[:, 1]  - 0.6*X[:, 4] +
           np.random.normal(scale = 0.01, size = size))

        Y_0_test = (0.1*X_test[:, 1] + 0.1*X_test[:, 4] +
           np.random.normal(scale = 0.01, size = test_size))
        Y_1_test = (0.3*X_test[:, 1] - 0.1*X_test[:, 4] +
           np.random.normal(scale = 0.01, size = test_size))
        Y_2_test = (-0.5*X_test[:, 1] - 0.5*X_test[:, 4] +
           np.random.normal(scale = 0.01, size = test_size))
        Y_3_test = (0.2*X_test[:, 1]  - 0.6*X_test[:, 4] +
           np.random.normal(scale = 0.01, size = test_size))

        tot_len = len(Y_0) + len(Y_1) + len(Y_2) + len(Y_3)
        l0 = len(Y_0)
        l1 = len(Y_1)
        l2 = len(Y_2)
        l3 = len(Y_3)

        tot_len_test = (len(Y_0_test) + len(Y_1_test) + len(Y_2_test)
                        + len(Y_3_test))
        l0_test = len(Y_0_test)
        l1_test = len(Y_1_test)
        l2_test = len(Y_2_test)
        l3_test = len(Y_3_test)

        self.X_train = np.zeros([tot_len, d*4])
        self.X_test = np.zeros([tot_len_test, d*4])
        done = 0
        done_test = 0
        for length, length_test, i in zip([l0, l1, l2, l3],
                [l0_test, l1_test, l2_test, l3_test], np.arange(1, 5)):
            new = done + length
            new_test = done_test + length_test
            # Feature values are shared across each target value, so repeat
            # 'X' and 'X_test' 
            self.X_train[done:new, (i - 1)*d:i*d] = X
            self.X_test[done_test:new_test, (i - 1)*d:i*d] = X_test
            done = new
            done_test = new_test
            
        # Store all target values in one array
        y_temp1 = np.append(Y_0, Y_1)
        y_temp2 = np.append(Y_2, Y_3)
        self.y_train = np.append(y_temp1, y_temp2)

        y_temp1 = np.append(Y_0_test, Y_1_test)
        y_temp2 = np.append(Y_2_test, Y_3_test)
        self.y_test = np.append(y_temp1, y_temp2)
        return self.X_train, self.y_train, self.X_test, self.y_test

    def test_sizes(self):

        """
        Sample from the posterior for different numbers of data points (given by
        'sizes' array), with at first spike and slab, then gaussian priors. Use
        these samples to get mean values of the weights, then work out the test
        error and store it for each size.
        """
        
        for size, i in zip(self.sizes, np.arange(0, self.number_sizes)):
            self.X_train, self.y_train, self.X_test,\
                          self.y_test = self.get_data(size)
            weights = np.zeros(self.multi_dim*self.dim)
            zs = np.zeros(self.dim)
            if self.gen_weights == True:
                sns = spike_n_slab.run_MCMC(self.X_train, self.y_train, 0.02,
                                            0.2, weights, zs, 0.5, 4, 100.0,
                                            prior = 'spike_n_slab',
                                            save_message = 'weights' + str(size),
                                            samples = 10000)
            sns_weights = np.genfromtxt(
                                'spike_slab_results\s_n_s_weights\weights'\
                                + str(size) + '.csv')
            if self.gen_weights == True:
                gauss = spike_n_slab.run_MCMC(self.X_train, self.y_train, 0.02,
                                              0.2, weights, zs, 0.5, 4, 100.0,
                                              prior = 'gauss',
                                     save_message = 'gauss_weights' + str(size),
                                              samples = 10000)
            gauss_weights = np.genfromtxt(
                'spike_slab_results\s_n_s_weights\gauss_weights'\
                                + str(size) + '.csv')
            n = self.multi_dim*self.dim
            sns_mean = np.zeros(n)
            gauss_mean = np.zeros(n)
            for j in range(n):
                # Discared first 1000 samples to ensure MCMC has reached
                # equilibrium, take mean of rest to get a guess for the weights
                sns_mean[j] = np.mean(sns_weights[1000:, j])
                gauss_mean[j] = np.mean(gauss_weights[1000:, j])
            mle_weights = MLE(self.X_train, self.y_train)
            y_sns, y_gauss, y_mle = predict(sns_mean, gauss_mean, mle_weights,
                                self.X_test, len(self.y_test))
            sns_err = np.mean((y_sns - self.y_test)**2)
            gauss_err = np.mean((y_gauss - self.y_test)**2)
            mle_err = np.mean((y_mle - self.y_test)**2)
            self.mle_out[i] = mle_err
            self.sns_out[i] = sns_err
            self.gauss_out[i] = gauss_err

    @staticmethod
    def make_mean(big_arr):

        """
        Manipulate big array of errors for differnt runs by taking logs (since
        they're strictly positive), then getting the mean for each size, then
        subtracting the global mean.

        :type big_arr: array of floats of size (length of sizes)*(number of runs)
        :param big_arr: array containing error for each size and run
        """
        
        mean_arr = np.log(big_arr)
        std = np.std(mean_arr, axis = 1)
        mean_arr = np.mean(mean_arr, axis = 1)
        mean = np.mean(mean_arr)
        mean_arr = mean_arr - mean
        return mean_arr, mean, std

    def test_runs(self):

        """
        Repeat test of sizes for the number of runs, and then store the mean of
        the runs for each size, after manipulating the errors.
        """
        
        for i in range(self.runs):
            self.test_sizes()
            self.big_mle_out[:, i] = self.mle_out
            self.big_sns_out[:, i] = self.sns_out
            self.big_gauss_out[:, i] = self.gauss_out
            
        # Take logs, record standard deviation and mean for each size, then
        # subtract the global mean (the mean across sizes, not runs). This last
        # step is to improve fitting a Gaussian process later. 
        self.mean_mle_out, mle_mean, mle_std = self.make_mean(self.big_mle_out)
        self.mean_sns_out, sns_mean, sns_std = self.make_mean(self.big_sns_out)
        (self.mean_gauss_out, gauss_mean,
                                gauss_std) = self.make_mean(self.big_gauss_out)
 
        return mle_std, sns_std, gauss_std, mle_mean, sns_mean, gauss_mean

def MLE(X, y):

    """
    Maximum likelihood estimate of weights

    :type X: array of size #data points*4 by #dimensions*4 containing floats
    :param X: matrix containing features for each data point

    :type y: array of size #data points*4 containing floats
    :param y: vector filled with target variables
    """
    
    Theta = np.matrix(X)
    Theta_t = np.matrix.transpose(Theta)
    inv = np.linalg.inv(Theta_t*Theta)
    return inv*Theta_t*matrix.transpose(matrix(y))

def predict(sns_weights, gauss_weights, max_like_est, X, size):

    """
    Take weights for the two priors and MLE and generate predicted y values
    given matrix of features X
    """
    
    y_sns = np.zeros(size)
    y_gauss = np.zeros(size)
    y_mle = np.zeros(size)
    for i in range(size):
            y_sns[i] = np.sum(sns_weights*X[i, :])
            y_gauss[i] = np.sum(gauss_weights*X[i, :])
            for j in range(X.shape[1]):
                y_mle[i] = y_mle[i] + float(max_like_est[j])*X[i, j]              
    return y_sns, y_gauss, y_mle

def fit_GP(xs, ys, std):

    """
    Fit Gaussian process with Matern kernel for errors against number of data
    points
    """
    
    X = np.zeros([len(xs), 2])
    X[:, 0] = 1.0
    X[:, 1] = xs
    gp = GaussianProcessRegressor(
            kernel=Matern(nu=2.5),
            alpha = std,
            n_restarts_optimizer=25,
        )
    gp.fit(X, ys)
    x = np.arange(3, 20, 0.005)
    X_pred = np.zeros([len(x), 2])
    X_pred[:, 0] = 1.0
    X_pred[:, 1] = x
    y, std = gp.predict(X_pred, return_std=True)
    y_plus = y + std
    y_minus = y - std
    return y, y_plus, y_minus, x

#-----------------------#
# Visualisation Section #
#-----------------------#
# Set this 'True' to generate new data and weights. 
new_data = False

if new_data == True:
    versus = Testing(sizes = [3, 4, 5, 6, 8, 10, 12, 16, 20], dim = 5, runs = 5)
    mle_std, sns_std, \
             gauss_std, mle_mean, sns_mean, gauss_mean = versus.test_runs()
    errors = [mle_std, sns_std, gauss_std, mle_mean, sns_mean, gauss_mean, versus]
    pickle.dump(errors, open('comparison.pickle', 'wb'))
else:
    load_name = 'comparison.pickle'
    errors = pickle.load( open( load_name, "rb" ) )
    mle_std, sns_std, gauss_std, mle_mean, sns_mean, gauss_mean, versus = errors

# Get data from our class which compares models. 
mle_out = versus.mean_mle_out
sns_out = versus.mean_sns_out
gauss_out = versus.mean_gauss_out
xs = versus.sizes

# Fit Gaussian process to the three models, make it return standard deviation.
y, y_plus, y_minus, x = fit_GP(xs, mle_out, mle_std)
y2, y2_plus, y2_minus, x = fit_GP(xs, sns_out, sns_std)
y3, y3_plus, y3_minus, x = fit_GP(xs, gauss_out, gauss_std)

xs = np.array(xs)
x = np.array(x)
# Times by four since there are four target variables.
xs *= 4
x *= 4

# Plot the three models for different numbers of data points.
plt.figure()
plt.scatter(xs, mle_out + mle_mean, s= 30, alpha=0.3,
                    edgecolor='black', facecolor='b', linewidth=0.75)
plt.errorbar(xs, mle_out + mle_mean, mle_std, fmt='b.', markersize=16,
             alpha=0.5, label = 'Maximum likelihood')
plt.scatter(xs, sns_out + sns_mean, s= 30, alpha=0.3,
                    edgecolor='black', facecolor='r', linewidth=0.75 )
plt.errorbar(xs, sns_out + sns_mean, sns_std, fmt='r.', markersize=16,
             alpha=0.5, label = 'Spike and slab prior')
plt.errorbar(xs, gauss_out + gauss_mean, gauss_std, fmt='g.',
             markersize=16, alpha=0.8, label = 'Gaussian prior')
plt.plot([0, 100], [np.log(0.0001), np.log(0.0001)], 'm--', linewidth = 3.0,
         alpha = 0.6, label = 'True Value')
plt.legend(loc='upper right', shadow=True)
plt.xlabel('$\mathrm{Number}$' + ' ' + '$\mathrm{of}$' + ' ' +
           '$\mathrm{data}$'+ ' ' + '$\mathrm{points}$', fontsize = 20)
plt.ylabel('$\mathrm{log(Error)}$', fontsize = 20)
plt.xlim(10.0, 82.0)
plt.ylim(-11, 25)
plt.xscale('log', basex=2)
plt.tight_layout()
plt.savefig('figures/errors.png')
plt.show()

# Plot just spike and slab and MLE, and plot Gaussian processes for those two. 
plt.figure()
plt.scatter(xs, mle_out + mle_mean, s= 30, alpha=0.3,
                    edgecolor='black', facecolor='b', linewidth=0.75)
plt.errorbar(xs, mle_out + mle_mean, mle_std, fmt='b.', markersize=16,
             alpha=0.5, label = 'Maximum likelihood')
plt.scatter(xs, sns_out + sns_mean, s= 30, alpha=0.3,
                    edgecolor='black', facecolor='r', linewidth=0.75 )
plt.errorbar(xs, sns_out + sns_mean, sns_std, fmt='r.', markersize=16,
             alpha=0.5, label = 'Spike and slab prior')
plt.plot(x, y + mle_mean)
plt.fill_between(x, y_plus + mle_mean, y_minus + mle_mean, alpha = 0.3)
plt.plot(x, y2 + sns_mean, color = 'red')
plt.fill_between(x, y2_plus + sns_mean, y2_minus + sns_mean,
                 alpha = 0.3, color = 'red')
plt.plot([0, 100], [np.log(0.0001), np.log(0.0001)], 'm--', linewidth = 3.0,
         alpha = 0.6, label = 'True Value')
plt.legend(loc='upper right', shadow=True)
plt.xlabel('$\mathrm{Number}$' + ' ' + '$\mathrm{of}$' + ' ' +
           '$\mathrm{data}$'+ ' ' + '$\mathrm{points}$', fontsize = 20)
plt.ylabel('$\mathrm{log(Error)}$', fontsize = 20)
plt.xlim(10.0, 82.0)
plt.ylim(-11, 8)
plt.tight_layout()
plt.xscale('log', basex=2)
plt.savefig('figures/errors_gp.png')
plt.show()

# Get posterior for p0 (posterior percentage of relevant features)
p0 = np.genfromtxt('spike_slab_results\s_n_s_p0\weights20.csv')

# Histogram with the  'Bayesian blocks' method for bin sizes from AstroPy
plt.figure()
hist(p0[1000:], bins = 'blocks', histtype='stepfilled', normed=True,
            color='b', alpha = 0.7)
plt.ylabel('$\mathrm{Frequency}$', fontsize = 20)
plt.xlabel('$p_0$', fontsize = 20)
plt.tight_layout()
plt.savefig('figures/p0.png')
plt.show()

# Get posterior for error 
sig2 = np.genfromtxt('spike_slab_results\s_n_s_sigma2\weights20.csv')

plt.figure()
hist(sig2[1000:], bins = 'freedman', histtype='stepfilled', normed=True,
            color='b', alpha = 0.7)
plt.ylabel('$\mathrm{Frequency}$', fontsize = 20)
plt.xlabel('$\sigma^2$', fontsize = 20)
plt.plot([0.0001, 0.0001], [0.0, 25000.0], 'r--', linewidth = 5.0,
         alpha = 0.6, label = 'True Value')
plt.legend(loc='upper right', shadow=True)
plt.ylim(0.0, 25000.0)
plt.tight_layout()
plt.savefig('figures/sig2.png')
plt.show()

plt.figure()
hist(np.log(sig2[1000:]), bins = 'freedman', histtype='stepfilled', normed=True,
            color='b', alpha = 0.7)
plt.plot([np.log(0.0001), np.log(0.0001)], [0.0, 100.0], 'r--', linewidth = 5.0,
         alpha = 0.6, label = 'True Value')
plt.legend(loc='upper right', shadow=True)
plt.ylabel('$\mathrm{Frequency}$', fontsize = 20)
plt.xlabel('$\mathrm{log}(\sigma^2)$', fontsize = 20)
plt.ylim(0.0, 2.8)
plt.tight_layout()
plt.savefig('figures/logsig2.png')
plt.show()

# Get posterior for weights of various numbers of data points.
w3 = np.genfromtxt('spike_slab_results\s_n_s_weights\weights3.csv')
w5 = np.genfromtxt('spike_slab_results\s_n_s_weights\weights5.csv')
w11 = np.genfromtxt('spike_slab_results\s_n_s_weights\weights11.csv')
w20 = np.genfromtxt('spike_slab_results\s_n_s_weights\weights20.csv')

weights = [w3[1000:, 1], w5[1000:, 1], w11[1000:, 1], w20[1000:, 1]]
titles = ['12', '20', '44', '80']
lims = [60.0, 40.0, 30.0, 180.0]
lims = iter(lims)

# Plot histograms of the four weights on a big figure.
plt.figure()
f, axes = plt.subplots(2, 2)
for weight, title, ax in zip(weights, titles, axes.flat):
    ax.hist(weight, bins = 'fd', histtype='stepfilled', normed=True,
            color='b', alpha = 0.7)
    ax.set_title('$' + title + '$' + ' ' + '$\mathrm{data}$' + ' '
                 + '$\mathrm{points}$', fontsize = 16)
    ax.plot([0.1, 0.1], [0.0, 300.0], 'r--', linewidth = 5.0,
         alpha = 0.6)
    ax.set_ylim(0, next(lims))
f.text(0.5, 0.02, '$\mathrm{Weights}$', ha='center', va='center',
       fontsize = 20)
f.text(0.02, 0.5, '$\mathrm{Frequency}$', ha='center',
         va='center', rotation='vertical', fontsize = 20)
plt.tight_layout()
plt.savefig('figures/weights.png')
plt.show()
    

