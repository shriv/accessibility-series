/*
* Simple Univariate Normal
*/

data {
    int n;
    real y[n];
}
transformed data {}
parameters {
    real<lower=0, upper=60> mu;
    real<lower=0, upper=20> sigma;
}
transformed parameters {}
model {
    y ~ normal(mu, sigma);
}
generated quantities {
    real y_pred;
    y_pred = normal_rng(mu, sigma);
}
