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
C(author_type)[T.Human]        |         0.3451  * |         0.3055  * |         0.2210   
C(dominant_language)[T.C#]     |        -2.8332*** |        -2.8890*** |        -0.9906***
C(dominant_language)[T.Go]     |        -2.9981*** |        -3.1748*** |        -1.3974***
C(dominant_language)[T.JavaScript] |        -3.0581*** |        -3.1174*** |        -1.3111 **
C(dominant_language)[T.Java]   |        -3.4819*** |        -3.5540*** |        -1.9498***
C(dominant_language)[T.Other]  |        -2.1621*** |        -2.3384*** |        -0.6190 **
C(dominant_language)[T.Python] |        -2.8774*** |        -3.0085*** |        -1.1515***
C(dominant_language)[T.Ruby]   |        -4.1096*** |        -4.2267*** |        -1.6035***
C(dominant_language)[T.Rust]   |        -2.3571*** |        -2.4532*** |        -1.0233***
C(dominant_language)[T.TypeScript] |        -2.2692*** |        -2.4035*** |        -0.6527***
C(dominant_language)[T.Unknown] |        -3.6851*** |        -3.7504*** |        -1.6408***
C(task_type)[T.fix]            |         0.1395    |         0.1238    |         0.0636   
Intercept                      |        -0.9149 ** |        -1.2837*** |        -2.9916***
log_file_heat                  |                  ─ |         0.3639 ** |         0.5753***
log_lines_added                |         0.2248*** |         0.2150*** |        -0.0298   
─────────────────────────────────────────────────────────────────────────────────────────────
N                              |                559 |                559 |                559
R²                             |             0.1182 |             0.1322 |             0.1239
Adj. R²                        |             0.0971 |             0.1099 |             0.1014
─────────────────────────────────────────────────────────────────────────────────────────────
```

*Significance: \*p<0.05, \*\*p<0.01, \*\*\*p<0.001*

## CR Baseline — Full Summary

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                 log_CR   R-squared:                       0.118
Model:                            OLS   Adj. R-squared:                  0.097
Method:                 Least Squares   F-statistic:                     1991.
Date:                Tue, 17 Mar 2026   Prob (F-statistic):          3.07e-136
Time:                        00:06:26   Log-Likelihood:                -1099.3
No. Observations:                 559   AIC:                             2227.
Df Residuals:                     545   BIC:                             2287.
Df Model:                          13                                         
Covariance Type:              cluster                                         
======================================================================================================
                                         coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------------------
Intercept                             -0.9149      0.305     -3.003      0.003      -1.512      -0.318
C(author_type)[T.Human]                0.3451      0.135      2.562      0.010       0.081       0.609
C(task_type)[T.fix]                    0.1395      0.229      0.610      0.542      -0.308       0.587
C(dominant_language)[T.C#]            -2.8332      0.230    -12.326      0.000      -3.284      -2.383
C(dominant_language)[T.Go]            -2.9981      0.383     -7.823      0.000      -3.749      -2.247
C(dominant_language)[T.Java]          -3.4819      0.689     -5.057      0.000      -4.831      -2.132
C(dominant_language)[T.JavaScript]    -3.0581      0.384     -7.968      0.000      -3.810      -2.306
C(dominant_language)[T.Other]         -2.1621      0.277     -7.793      0.000      -2.706      -1.618
C(dominant_language)[T.Python]        -2.8774      0.197    -14.616      0.000      -3.263      -2.492
C(dominant_language)[T.Ruby]          -4.1096      0.610     -6.738      0.000      -5.305      -2.914
C(dominant_language)[T.Rust]          -2.3571      0.192    -12.268      0.000      -2.734      -1.980
C(dominant_language)[T.TypeScript]    -2.2692      0.235     -9.636      0.000      -2.731      -1.808
C(dominant_language)[T.Unknown]       -3.6851      0.221    -16.643      0.000      -4.119      -3.251
log_lines_added                        0.2248      0.041      5.504      0.000       0.145       0.305
==============================================================================
Omnibus:                      466.263   Durbin-Watson:                   1.631
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               35.391
Skew:                           0.019   Prob(JB):                     2.07e-08
Kurtosis:                       1.768   Cond. No.                         223.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

## CR + Heat — Full Summary

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                 log_CR   R-squared:                       0.132
Model:                            OLS   Adj. R-squared:                  0.110
Method:                 Least Squares   F-statistic:                     197.1
Date:                Tue, 17 Mar 2026   Prob (F-statistic):           4.56e-77
Time:                        00:06:26   Log-Likelihood:                -1094.8
No. Observations:                 559   AIC:                             2220.
Df Residuals:                     544   BIC:                             2285.
Df Model:                          14                                         
Covariance Type:              cluster                                         
======================================================================================================
                                         coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------------------
Intercept                             -1.2837      0.332     -3.870      0.000      -1.934      -0.634
C(author_type)[T.Human]                0.3055      0.140      2.187      0.029       0.032       0.579
C(task_type)[T.fix]                    0.1238      0.232      0.534      0.593      -0.331       0.578
C(dominant_language)[T.C#]            -2.8890      0.231    -12.493      0.000      -3.342      -2.436
C(dominant_language)[T.Go]            -3.1748      0.407     -7.799      0.000      -3.973      -2.377
C(dominant_language)[T.Java]          -3.5540      0.698     -5.091      0.000      -4.922      -2.186
C(dominant_language)[T.JavaScript]    -3.1174      0.397     -7.845      0.000      -3.896      -2.339
C(dominant_language)[T.Other]         -2.3384      0.250     -9.344      0.000      -2.829      -1.848
C(dominant_language)[T.Python]        -3.0085      0.201    -14.966      0.000      -3.403      -2.615
C(dominant_language)[T.Ruby]          -4.2267      0.618     -6.843      0.000      -5.437      -3.016
C(dominant_language)[T.Rust]          -2.4532      0.200    -12.292      0.000      -2.844      -2.062
C(dominant_language)[T.TypeScript]    -2.4035      0.235    -10.246      0.000      -2.863      -1.944
C(dominant_language)[T.Unknown]       -3.7504      0.232    -16.131      0.000      -4.206      -3.295
log_lines_added                        0.2150      0.040      5.412      0.000       0.137       0.293
log_file_heat                          0.3639      0.115      3.168      0.002       0.139       0.589
==============================================================================
Omnibus:                      268.179   Durbin-Watson:                   1.653
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               31.156
Skew:                           0.031   Prob(JB):                     1.72e-07
Kurtosis:                       1.845   Cond. No.                         233.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

## RF + Heat — Full Summary

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                 log_RF   R-squared:                       0.124
Model:                            OLS   Adj. R-squared:                  0.101
Method:                 Least Squares   F-statistic:                     350.8
Date:                Tue, 17 Mar 2026   Prob (F-statistic):           6.58e-92
Time:                        00:06:26   Log-Likelihood:                -959.15
No. Observations:                 559   AIC:                             1948.
Df Residuals:                     544   BIC:                             2013.
Df Model:                          14                                         
Covariance Type:              cluster                                         
======================================================================================================
                                         coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------------------
Intercept                             -2.9916      0.206    -14.508      0.000      -3.396      -2.587
C(author_type)[T.Human]                0.2210      0.126      1.757      0.079      -0.026       0.467
C(task_type)[T.fix]                    0.0636      0.127      0.501      0.617      -0.185       0.313
C(dominant_language)[T.C#]            -0.9906      0.258     -3.838      0.000      -1.496      -0.485
C(dominant_language)[T.Go]            -1.3974      0.237     -5.904      0.000      -1.861      -0.934
C(dominant_language)[T.Java]          -1.9498      0.288     -6.780      0.000      -2.513      -1.386
C(dominant_language)[T.JavaScript]    -1.3111      0.416     -3.153      0.002      -2.126      -0.496
C(dominant_language)[T.Other]         -0.6190      0.202     -3.064      0.002      -1.015      -0.223
C(dominant_language)[T.Python]        -1.1515      0.180     -6.406      0.000      -1.504      -0.799
C(dominant_language)[T.Ruby]          -1.6035      0.416     -3.857      0.000      -2.418      -0.789
C(dominant_language)[T.Rust]          -1.0233      0.141     -7.259      0.000      -1.300      -0.747
C(dominant_language)[T.TypeScript]    -0.6527      0.190     -3.427      0.001      -1.026      -0.279
C(dominant_language)[T.Unknown]       -1.6408      0.176     -9.333      0.000      -1.985      -1.296
log_lines_added                       -0.0298      0.040     -0.751      0.453      -0.108       0.048
log_file_heat                          0.5753      0.103      5.563      0.000       0.373       0.778
==============================================================================
Omnibus:                       17.763   Durbin-Watson:                   1.744
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               18.515
Skew:                           0.427   Prob(JB):                     9.54e-05
Kurtosis:                       2.741   Cond. No.                         233.
==============================================================================

Notes:
[1] Standard Errors are robust to cluster correlation (cluster)
```

