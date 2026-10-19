"""Distributions, matrix repair and a Gaussian copula -- all stdlib.

No numpy. Everything here is implemented directly so the package runs anywhere
a Python interpreter does, including on a laptop in a sportsbook parking lot.
"""

import math
import random

SQRT2 = math.sqrt(2.0)

# --------------------------------------------------------------- normal basics


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# Acklam's inverse normal CDF, refined with one Halley step. Accurate to
# roughly 1e-15 -- more than enough for simulation work.
_A = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
      1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
_B = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
      6.680131188771972e+01, -1.328068155288572e+01)
_C = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
      -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
_D = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
      3.754408661907416e+00)


def norm_ppf(p):
    """Inverse standard-normal CDF."""
    if not 0.0 < p < 1.0:
        if p <= 0.0:
            return -8.0
        return 8.0
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
            ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    elif p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / \
            ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    else:
        q = p - 0.5
        r = q * q
        x = (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / \
            (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
    # Halley refinement
    e = norm_cdf(x) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


# ------------------------------------------------------------- count marginals


def poisson_cdf(k, lam):
    if k < 0:
        return 0.0
    total = 0.0
    term = math.exp(-lam)
    for i in range(int(k) + 1):
        if i > 0:
            term *= lam / i
        total += term
    return min(total, 1.0)


def poisson_ppf(u, lam):
    """Smallest k with CDF(k) >= u."""
    if lam <= 0:
        return 0
    k = 0
    term = math.exp(-lam)
    total = term
    limit = int(lam + 12.0 * math.sqrt(lam) + 30)
    while total < u and k < limit:
        k += 1
        term *= lam / k
        total += term
    return k


def negbin_ppf(u, mean, variance):
    """Negative binomial by mean/variance -- Poisson with the overdispersion
    real box scores actually show (a receiver's target count is not Poisson;
    game script fattens both tails)."""
    if variance <= mean:
        return poisson_ppf(u, mean)
    p = mean / variance
    r = mean * p / (1.0 - p)
    # cumulative search on the pmf recurrence
    prob = p ** r
    total = prob
    k = 0
    limit = int(mean + 15.0 * math.sqrt(variance) + 50)
    while total < u and k < limit:
        k += 1
        prob *= (r + k - 1.0) / k * (1.0 - p)
        total += prob
    return k


# ------------------------------------------------------- correlation matrices


def cholesky(matrix):
    """Lower-triangular Cholesky factor. Raises if not positive definite."""
    n = len(matrix)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                d = matrix[i][i] - s
                if d <= 1e-12:
                    raise ValueError("matrix is not positive definite")
                L[i][j] = math.sqrt(d)
            else:
                L[i][j] = (matrix[i][j] - s) / L[j][j]
    return L


def _jacobi_eigen(matrix, sweeps=100, tol=1e-12):
    """Symmetric eigendecomposition by cyclic Jacobi rotations."""
    n = len(matrix)
    a = [row[:] for row in matrix]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(sweeps):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-15:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p] = c * vkp - s * vkq
                    v[k][q] = s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def nearest_correlation(matrix, epsilon=1e-8):
    """Repair a correlation matrix that isn't positive semi-definite.

    Hand-entered correlations are routinely impossible -- claim A/B = 0.9,
    B/C = 0.9 and A/C = -0.5 and no joint distribution exists. Rather than
    crash on a bad guess, clip the negative eigenvalues and renormalise the
    diagonal back to 1. The returned matrix is the closest legal one.
    """
    n = len(matrix)
    sym = [[0.5 * (matrix[i][j] + matrix[j][i]) for j in range(n)] for i in range(n)]
    vals, vecs = _jacobi_eigen(sym)
    if min(vals) > epsilon:
        return sym
    clipped = [max(v, epsilon) for v in vals]
    out = [[sum(vecs[i][k] * clipped[k] * vecs[j][k] for k in range(n))
            for j in range(n)] for i in range(n)]
    # renormalise so the diagonal is exactly 1
    d = [math.sqrt(out[i][i]) for i in range(n)]
    return [[out[i][j] / (d[i] * d[j]) for j in range(n)] for i in range(n)]


def is_positive_definite(matrix):
    try:
        cholesky(matrix)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- the copula


class GaussianCopula:
    """Draws correlated uniforms, which each leg then maps through its own
    marginal distribution.

    This is the machine that makes a same-game parlay honest. Legs are not
    independent coin flips: when the quarterback throws for 340 the receiver
    almost certainly cleared his yardage number too. The copula keeps the
    dependence structure while letting every leg keep its own shape.
    """

    def __init__(self, correlation, rng=None):
        self.n = len(correlation)
        self.correlation = nearest_correlation(correlation)
        self.chol = cholesky([[self.correlation[i][j] + (1e-10 if i == j else 0.0)
                               for j in range(self.n)] for i in range(self.n)])
        self.rng = rng or random.Random()

    def sample_normals(self):
        z = [self.rng.gauss(0.0, 1.0) for _ in range(self.n)]
        return [sum(self.chol[i][k] * z[k] for k in range(i + 1)) for i in range(self.n)]

    def sample_uniforms(self):
        return [norm_cdf(x) for x in self.sample_normals()]


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def wilson_interval(successes, trials, z=1.96):
    """Confidence interval on a hit rate. Jordan quotes this instead of letting
    anyone brag about 7-3."""
    if trials == 0:
        return (0.0, 1.0)
    p = successes / trials
    denom = 1.0 + z * z / trials
    centre = (p + z * z / (2.0 * trials)) / denom
    margin = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))
