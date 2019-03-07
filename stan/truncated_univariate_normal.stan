/*
* Truncated Univariate Normal
*/

functions {
    real normal_lub_rng(real mu, real sigma, real lb, real ub) {
        real p_lb = normal_cdf(lb, mu, sigma);
        real p_ub = normal_cdf(ub, mu, sigma);
        real u = uniform_rng(p_lb, p_ub);
        real y = mu + (sigma * Phi(u));
return y; }
}
data {
    int N;
    real L;
    real U;
    real<lower=L, upper=U> y[N];
}
parameters {
    real<lower=0, upper=60> mu;
    real<lower=0, upper=20> sigma;
}
model {
    for (n in 1:N)
        y[n] ~ normal(mu, sigma) T[L,U];
        }
generated quantities {
    real y_pred;
    y_pred = normal_lub_rng(mu, sigma, L, U);
}
