# RQ3b: Regression Analysis Results

## Research Question
Does AI code churn less because it's genuinely more stable, or because it lands in less active (colder) parts of the codebase?

## Models
| Model | Formula | Purpose |
|-------|---------|----------|
| Model 1 | `log_CR ~ author_type + log_lines_added + task_type + language` | Baseline |
| Model 2 | `log_CR ~ ... + log_file_heat` | Does file heat explain the AI effect? |
| Model 3 | `log_RF ~ ... + log_file_heat` | Confirm with churn frequency |

## Comparison Table

```
─────────────────────────────────────────────────────────────────────────────────────────────
Predictor                      |        CR Baseline |          CR + Heat |          RF + Heat
─────────────────────────────────────────────────────────────────────────────────────────────
C(author_type)[T.Human]        |         0.1297    |         0.1003    |         0.1293   
C(dominant_language)[T.Go]     |         0.3887*** |         0.3673*** |        -0.4732***
C(dominant_language)[T.JavaScript] |         0.2722    |         0.2716    |        -0.8913   
C(dominant_language)[T.Other]  |         0.8561    |         0.7274    |         0.2969   
C(dominant_language)[T.Python] |        -0.4361  * |        -0.4536  * |        -0.3204   
C(dominant_language)[T.Rust]   |         0.3812  * |         0.3836 ** |        -0.1043   
C(dominant_language)[T.TypeScript] |         0.7302  * |         0.6352    |         0.3272   
C(task_type)[T.fix]            |         0.1902    |         0.1077    |         0.2391   
Intercept                      |        -3.6201*** |        -4.0723*** |        -3.9167***
log_file_heat                  |                  ─ |         0.3937 ** |         0.6482***
log_lines_added                |         0.2460*** |         0.2328*** |        -0.0334   
─────────────────────────────────────────────────────────────────────────────────────────────
N                              |                268 |                268 |                268
R²                             |             0.1449 |             0.1638 |             0.1833
Adj. R²                        |             0.1151 |             0.1312 |             0.1515
─────────────────────────────────────────────────────────────────────────────────────────────
```

*Significance: \*p<0.05, \*\*p<0.01, \*\*\*p<0.001*

## CR Baseline — Full Summary

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                 log_CR   R-squared:                       0.145
Model:                            OLS   Adj. R-squared:                  0.115
Method:                 Least Squares   F-statistic:                 4.376e+11
Date:                Sun, 08 Mar 2026   Prob (F-statistic):           5.55e-84
Time:                        21:34:26   Log-Likelihood:                -512.57
No. Observations:                 268   AIC:                             1045.
Df Residuals:                     258   BIC:                             1081.
Df Model:                           9                                         
Covariance Type:              cluster                                         
======================================================================================================
                                         coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------------------
Intercept                             -3.6201      0.407     -8.894      0.000      -4.418      -2.822
C(author_type)[T.Human]                0.1297      0.160      0.811      0.417      -0.184       0.443
C(task_type)[T.fix]                    0.1902      0.345      0.552      0.581      -0.485       0.866
C(dominant_language)[T.Go]             0.3887      0.099      3.920      0.000       0.194       0.583
C(dominant_language)[T.JavaScript]     0.2722      0.404      0.674      0.500      -0.519       1.064
C(dominant_language)[T.Other]          0.8561      0.510      1.679      0.093      -0.143       1.856
C(dominant_language)[T.Python]        -0.4361      0.183     -2.380      0.017      -0.795      -0.077
C(dominant_language)[T.Rust]           0.3812      0.155      2.454      0.014       0.077       0.686
C(dominant_language)[T.TypeScript]     0.7302      0.353      2.067      0.039       0.038       1.422
log_lines_added                        0.2460      0.052      4.690      0.000       0.143       0.349
==============================================================================
Omnibus:                       59.581   Durbin-Watson:                   1.679
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               12.888
Skew:                          -0.135   Prob(JB):                      0.00159
Kurtosis:                       1.960   Cond. No.                         51.0
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

## CR + Heat — Full Summary

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                 log_CR   R-squared:                       0.164
Model:                            OLS   Adj. R-squared:                  0.131
Method:                 Least Squares   F-statistic:                     17.09
Date:                Sun, 08 Mar 2026   Prob (F-statistic):           2.40e-06
Time:                        21:34:26   Log-Likelihood:                -509.59
No. Observations:                 268   AIC:                             1041.
Df Residuals:                     257   BIC:                             1081.
Df Model:                          10                                         
Covariance Type:              cluster                                         
======================================================================================================
                                         coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------------------
Intercept                             -4.0723      0.488     -8.348      0.000      -5.028      -3.116
C(author_type)[T.Human]                0.1003      0.171      0.587      0.557      -0.234       0.435
C(task_type)[T.fix]                    0.1077      0.340      0.317      0.752      -0.559       0.774
C(dominant_language)[T.Go]             0.3673      0.108      3.411      0.001       0.156       0.578
C(dominant_language)[T.JavaScript]     0.2716      0.484      0.561      0.575      -0.678       1.221
C(dominant_language)[T.Other]          0.7274      0.459      1.585      0.113      -0.172       1.627
C(dominant_language)[T.Python]        -0.4536      0.181     -2.510      0.012      -0.808      -0.099
C(dominant_language)[T.Rust]           0.3836      0.137      2.804      0.005       0.115       0.652
C(dominant_language)[T.TypeScript]     0.6352      0.345      1.842      0.066      -0.041       1.311
log_lines_added                        0.2328      0.046      5.049      0.000       0.142       0.323
log_file_heat                          0.3937      0.133      2.970      0.003       0.134       0.654
==============================================================================
Omnibus:                       40.410   Durbin-Watson:                   1.735
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               10.718
Skew:                          -0.102   Prob(JB):                      0.00470
Kurtosis:                       2.042   Cond. No.                         53.2
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

## RF + Heat — Full Summary

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                 log_RF   R-squared:                       0.183
Model:                            OLS   Adj. R-squared:                  0.151
Method:                 Least Squares   F-statistic:                     34.66
Date:                Sun, 08 Mar 2026   Prob (F-statistic):           1.94e-08
Time:                        21:34:26   Log-Likelihood:                -432.38
No. Observations:                 268   AIC:                             886.8
Df Residuals:                     257   BIC:                             926.3
Df Model:                          10                                         
Covariance Type:              cluster                                         
======================================================================================================
                                         coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------------------
Intercept                             -3.9167      0.412     -9.506      0.000      -4.724      -3.109
C(author_type)[T.Human]                0.1293      0.172      0.750      0.453      -0.209       0.467
C(task_type)[T.fix]                    0.2391      0.193      1.238      0.216      -0.139       0.618
C(dominant_language)[T.Go]            -0.4732      0.120     -3.936      0.000      -0.709      -0.238
C(dominant_language)[T.JavaScript]    -0.8913      0.768     -1.161      0.246      -2.396       0.614
C(dominant_language)[T.Other]          0.2969      0.293      1.012      0.311      -0.278       0.872
C(dominant_language)[T.Python]        -0.3204      0.166     -1.933      0.053      -0.645       0.004
C(dominant_language)[T.Rust]          -0.1043      0.115     -0.905      0.365      -0.330       0.122
C(dominant_language)[T.TypeScript]     0.3272      0.247      1.324      0.185      -0.157       0.811
log_lines_added                       -0.0334      0.072     -0.467      0.641      -0.174       0.107
log_file_heat                          0.6482      0.092      7.017      0.000       0.467       0.829
==============================================================================
Omnibus:                        5.865   Durbin-Watson:                   1.773
Prob(Omnibus):                  0.053   Jarque-Bera (JB):                3.758
Skew:                           0.108   Prob(JB):                        0.153
Kurtosis:                       2.461   Cond. No.                         53.2
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

