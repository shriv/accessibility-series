/*
* Univariate normal with single level hierarchy
* Has lower bound truncation
*/
data {
  int<lower=0> N;                       // number of obs
  int<lower=1> level[N];                // level ID
  int<lower=0> L;                       // number of unique levels
  real l;                               // lower bound
  vector<lower=l>[N] y;                 // observed vals
}
parameters {
  vector<lower=0,upper=60>[L] mu_l;      // mean per level
  vector<lower=0,upper=30>[L] sigma_l;   // variance per level
  real<lower=0,upper=30> sigma_m;        // one grand sigma for mu
  real<lower=0,upper=60> mu_m;           // one grand mean for mu
  real<lower=0,upper=30> sigma_s;        // one grand sigma for sigma
  real<lower=0,upper=60> mu_s;           // one grand mu for sigma
}
model {
  mu_m ~ normal(0,100);                  // prior on grand mean for mu
  for (i in 1:L) {
    mu_l[i] ~ normal(mu_m, sigma_m);     // normal likelihood for level mean
    sigma_l[i] ~ normal(mu_s,sigma_s);   // normal likelihood for level sigma
    }

  for (i in 1:N) {
    y[i] ~ normal(mu_l[level[i]], sigma_l[level[i]]) T[l,];
  }
}
