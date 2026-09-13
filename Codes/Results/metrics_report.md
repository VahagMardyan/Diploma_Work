# Consolidated Power Prediction Evaluation Report

## Dataset: `filter`

![Power Analysis - filter](power_analysis_filter.png)

| Target | MAE (uW) | R2 Score | sMAPE (%) | MAPE (>0.1uW) |
| :--- | :--- | :--- | :--- | :--- |
| Total Power | 1.0519 | 0.9852 | 6.12% | 5.96% |
| Dynamic Power | 0.9260 | 0.9830 | 6.71% | 6.54% |
| Leakage Power | 0.2433 | 0.9901 | 6.76% | 6.79% |

---

## Dataset: `encoder`

![Power Analysis - encoder](power_analysis_encoder.png)

| Target | MAE (uW) | R2 Score | sMAPE (%) | MAPE (>0.1uW) |
| :--- | :--- | :--- | :--- | :--- |
| Total Power | 0.0113 | 0.9823 | 11.01% | 7.06% |
| Dynamic Power | 0.0050 | 0.9974 | 7.28% | 3.10% |
| Leakage Power | 0.0079 | 0.5393 | 45.23% | 68.77% |

---

## Dataset: `decoder`

![Power Analysis - decoder](power_analysis_decoder.png)

| Target | MAE (uW) | R2 Score | sMAPE (%) | MAPE (>0.1uW) |
| :--- | :--- | :--- | :--- | :--- |
| Total Power | 0.0071 | 0.9988 | 3.36% | 1.76% |
| Dynamic Power | 0.0066 | 0.9991 | 4.57% | 1.61% |
| Leakage Power | 0.0038 | 0.9591 | 12.92% | 13.07% |

---

## Dataset: `dataset`

![Power Analysis - dataset](power_analysis_dataset.png)

| Target | MAE (uW) | R2 Score | sMAPE (%) | MAPE (>0.1uW) |
| :--- | :--- | :--- | :--- | :--- |
| Total Power | 6.3645 | 0.9418 | 32.18% | 20.81% |
| Dynamic Power | 6.3583 | 0.9409 | 35.77% | 22.63% |
| Leakage Power | 0.0562 | 0.9933 | 17.36% | 6.82% |

---

## Dataset: `tests`

![Power Analysis - tests](power_analysis_tests.png)

| Target | MAE (uW) | R2 Score | sMAPE (%) | MAPE (>0.1uW) |
| :--- | :--- | :--- | :--- | :--- |
| Total Power | 3.0368 | 0.9957 | 21.74% | 18.72% |
| Dynamic Power | 3.0698 | 0.9955 | 24.04% | 20.41% |
| Leakage Power | 0.0555 | 0.9865 | 10.55% | 9.55% |

---

