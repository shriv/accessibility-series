/*
* Truncated Univariate Normal: Lower Bound Only
*/

functions {
    real normal_lb_rng(real mu, real sigma, real lb) {
        real p = normal_cdf(lb, mu, sigma);
        real u = uniform_rng(p, 1);
        real y = (sigma * inv_Phi(u)) + mu;
        return y;
    }
}
data {
    int N;
    real L;
    real U;
    real<lower=L> y[N];
}
parameters {
    real<lower=0, upper=60> mu;
    real<lower=0, upper=20> sigma;
}
model {
    for (n in 1:N)
        y[n] ~ normal(mu, sigma) T[L,];
        }
generated quantities {
    real y_pred;
    y_pred = normal_lb_rng(mu, sigma, L);
}
