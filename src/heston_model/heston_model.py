import numpy as np
import scipy.integrate as integrate

class HestonModel():

    def __init__(self, s, k, t, v, r, theta, kappa, sigma, rho):
        """
        :param s: stock price
        :param k: strike price
        :param t: time to maturity in years
        :param v: volatility
        :param r: risk free rate
        :param theta: long run average volatility (vbar)
        :param kappa: mean reversion (speed) of variance to long run average
        :param sigma: volatility of volatility (vvol)
        :param rho: correlation between the brownian motion of the stock price and the volatility.
        """
        self.s = s
        self.k = k
        self.t = t
        self.v = v
        self.r = r
        self.theta = theta
        self.kappa = kappa
        self.sigma = sigma
        self.rho = rho

    def characteristic_function(self, phi, j):
        """
        - The characteristic function is the Fourier transform of the probability density function (PDF)
        - Why use them instead of PDF?
            - Hard to obtain a closed form solution with PDF. CF's are able to obtain closed form solutions.
        - What does it allow me to do?
            - Get the probabilities, P1 and P2, which are the delta of the option
                and the risk neutral probability the option will be exercised.

        :param phi:
        :param j: either 1 or 2, so it runs through both probability functions P1 and P2.
        :return: The characteristic function of the log of the stock price.
        """
        if j == 1:
            u = 0.5
            b = self.kappa - self.rho * self.sigma

        else:
            u = -0.5
            b = self.kappa

        a = (self.kappa * self.theta)

        # Since we are getting the CF of the log of the stock price.
        x = np.log(self.s)

        d = np.sqrt((self.rho * self.sigma * phi * complex(0, 1) - b)**2
                    - self.sigma ** 2 * (2 * u * phi * complex(0, 1) - phi**2))

        # The Heston Model presented within his paper (link below) suffers from discontinuities when
        # the complex logarithm is restricted to its principal branch. This can lead to incorrect option prices.
        #   (principal value of the complex square root d is selected)
        # Link: http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.139.3204&rep=rep1&type=pdf

        # Below is a formula that is continuous when the complex logarithm is restricted to its principal branch.
        # This was shown by Load & Kalh in "Complex logarithms in Heston-like models" 2008, link below
        # http: // www.rogerlord.com / complexlogarithmsheston.pdf
        # I have used their version of it below. Summary of differences:
        #   1. g is equivalent to the inverse of Heston's  g.
        #   2. the d's are added or subtracted with the opposite sign to that in Heston's paper.

        # formula 9 within Lord & Kalh.
        g = (b - self.rho * self.sigma * phi * complex(0, 1) - d) / \
            (b - self.rho * self.sigma * phi * complex(0, 1) + d)

        # c = the first coefficient within the characteristic function, f
        C = self.r * phi * complex(0, 1) * self.t \
            + (a / (self.sigma ** 2)) * ((b - self.rho * self.sigma * phi * complex(0, 1) - d)*self.t \
                                         - 2 * np.log((1 - g * np.exp(-d * self.t)) / (1-g)))

        # dd = the second coefficient within the characteristic function
        D = ((b - self.rho * self.sigma * phi * complex(0, 1) - d) /\
             (self.sigma ** 2)) * ((1 - np.exp(-d * self.t)) / (1 - g * np.exp(-d * self.t)))

        f = np.exp(C + D * self.v + complex(0, 1) * phi * x)
        return a, b, d, g, C,  D, f

    def integrand(self, phi, j):

        (a, b, d, g, C,  D, f) = self.characteristic_function(phi, j)

        integrand = np.real(np.exp(-phi * complex(0, 1) * np.log(self.k)) * f / (phi * complex(0, 1)))
        return integrand

    def probability_function(self, j):
        """

        :param j:  either 1 or 2, so it runs through both probability functions P1 and P2.
        :return: Returns
            - P1 = The options delta
            - P2 = The risk neutral probability of exercise.
        """

        integrated = integrate.quad(self.integrand, 0, np.inf, args=j)
        # integrate.quad(self.integrand, lower limit, upper limit, args= extra arguments to pass through function )
        p = 0.5 + (1 / np.pi) * integrated[0]
        return p

    def european_call(self):
        call_price = self.s * (self.probability_function(1)) \
                     - self.k * np.exp(-self.r * self.t) * (self.probability_function(2))
        return call_price

    def european_put(self):
        put_price = self.k * (1-self.probability_function(2)) - self.s * (1-self.probability_function(1))
        return put_price

    def prob_of_exercise(self):
        """
        Probability of exercising the option
        """
        prob_of_exercise = self.probability_function(2)
        return prob_of_exercise

    def greek_delta(self):
        delta = self.probability_function(1)
        return delta

    def greek_integrand_gamma(self, phi):
        (a, b_1, d_1, g_1, C_1, D_1, f_1) = self.characteristic_function(phi, 1)
        (a, b_2, d_2, g_2, C_2, D_2, f_2) = self.characteristic_function(phi, 2)

        integrand_gamma = np.real(np.exp(-complex(0, 1) * phi * np.log(self.k)) * (1 / self.s * (1 + complex(0, 1) / phi) * f_1 + self.k * np.exp(-self.r * self.t) / self.s ** 2 * (1 - complex(0, 1) * phi) * f_2))
        return integrand_gamma

    def greek_gamma(self):
        gamma = 1/np.pi * integrate.quad(self.greek_integrand_gamma, 0, np.inf)[0]
        return gamma

    def greek_integrand_vega(self, phi):

        (a, b_1, d_1, g_1, C_1, D_1, f_1) = self.characteristic_function(phi, 1)
        (a, b_2, d_2, g_2, C_2, D_2, f_2) = self.characteristic_function(phi, 2)

        # Doing some algebra to get into one statement. Bring in S and K, then exp( phi * i * ln(K)) is common.
        integrand_vega = np.real(
            ((np.exp(-complex(0, 1) * phi * np.log(self.k))) * (self.s * f_1 * D_1 - self.k * np.exp(-self.r * self.t) * f_2 * D_2)) /
            (phi*complex(0, 1))
        )
        return integrand_vega

    def greek_vega(self):
        vega = (1/np.pi) * integrate.quad(self.greek_integrand_vega, 0, np.inf)[0]
        return vega

    def greek_integrand_rho(self, phi):

        (a, b_1, d_1, g_1, C_1, D_1, f_1) = self.characteristic_function(phi, 1)
        (a, b_2, d_2, g_2, C_2, D_2, f_2) = self.characteristic_function(phi, 2)

        integrand_rho = np.real( np.exp(-complex(0,1) * phi * np.log(self.k)) * (self.s * f_1 - self.k*(np.exp(-self.r*self.t))*(1/(-complex(0,1) * phi) +1)*f_2))

        return integrand_rho

    def greek_rho(self):
        rho = (0.5 * self.k * self.t)*np.exp(-self.r * self.t) + (self.t/np.pi)* integrate.quad(self.greek_integrand_rho, 0, np.inf)[0]
        return rho

    def dC_dt(self, phi, j):
        (a, b, d, g, C, D, f) = self.characteristic_function(phi, j)

        dC_dt = self.r * phi * complex(0, 1) + a / self.sigma ** 2 * ((b - self.rho * self.sigma * phi * complex(0, 1) - d) - (2 * d * g * np.exp(-d * self.t)) / (1 - g * np.exp(-d * self.t)))



        return dC_dt

    def dD_dt(self, phi, j):
        (a, b, d, g, C, D, f) = self.characteristic_function(phi, j)

        dD_dt = ((b - self.rho * self.sigma * phi * complex(0, 1) - d) / (self.sigma ** 2)) * (d * np.exp(-d * self.t) / (1 - g * np.exp(-d * self.t)) - ((1 - np.exp(-d * self.t)) * (d * g * np.exp(-d * self.t))) / (1 - g * np.exp(-d * self.t))**2)
        return dD_dt

    def greek_integrand_theta(self, phi):
        (a, b_1, d_1, g_1, C_1, D_1, f_1) = self.characteristic_function(phi, 1)
        (a, b_2, d_2, g_2, C_2, D_2, f_2) = self.characteristic_function(phi, 2)

        # TO DO: add in the char func as inputs into dc_dt so it is not run twice.
        dC_dt_1 = self.dC_dt(phi, 1)
        dC_dt_2 = self.dC_dt(phi, 2)

        dD_dt_1 = self.dD_dt(phi, 1)
        dD_dt_2 = self.dD_dt(phi, 2)

        integrand_theta = np.real(np.exp(-complex(0, 1) * phi * np.log(self.k)) / (phi * complex(0,1)) * ((dC_dt_1 + dD_dt_1 * self.v) * f_1 * self.s   - (self.r + dC_dt_2 + dD_dt_2* self.v) * f_2 * self.k * np.exp(-self.r * self.t)))
        return integrand_theta

    def greek_theta(self):
        print(integrate.quad(self.greek_integrand_theta, 0, np.inf)[0])
        theta = -(self.k * self.r * np.exp(-self.r * self.t)/2) + (1 / np.pi) * integrate.quad(self.greek_integrand_theta, 0, np.inf)[0]
        return theta




hest = HestonModel(s=154.08, k=147, t=1/365, v=0.0105, r=0.1, theta=0.0837, kappa=74.32, sigma=3.4532, rho=-0.8912)
hest_2 = HestonModel(s=1, k=2, t=10, v=0.16, r=0, theta=0.16, kappa=1, sigma=2, rho=-0.8)