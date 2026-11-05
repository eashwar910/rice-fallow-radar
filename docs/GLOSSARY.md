# Glossary

Plain-language meanings of terms used in the project. Useful for writing too — the supervisor asked that domain terms be explained before they're used.

## Agriculture

| Term | Meaning |
|---|---|
| **Kharif** | The monsoon cropping season (roughly June–November). Rice is the main kharif crop in eastern India. |
| **Rabi** | The dry winter cropping season (roughly November–March). |
| **Rice fallow** | Land that grows rice in kharif and is left empty in rabi. |
| **Pulse** | Edible legume seed — lentil, black gram, green gram, grasspea, chickpea. Fixes nitrogen; can grow on residual moisture. |
| **Residual moisture** | Water left in the soil after the rice crop, which a winter pulse can use without irrigation. It declines quickly after harvest. |
| **Relay sowing / paira / utera** | Broadcasting pulse seed into the standing rice shortly (about 1–3 weeks) before harvest, so it germinates on the remaining moisture. |
| **Zero-till sowing** | Placing seed into unploughed soil just after harvest, saving time and moisture. |
| **Sowing window** | The period when a field can be sown successfully. Here it has two edges: it opens when the field is harvested and not waterlogged, and closes when the soil becomes too dry. |
| **Waterlogging** | Soil saturated or flooded so machinery and seed can't be placed and seed may rot. Common on coastal lowlands. |
| **Trafficability / workability** | Whether soil can bear an operation (trafficability) and whether the operation succeeds without damage (workability). |
| **Establishment** | A seed germinating and becoming a viable seedling. |
| **Phenology** | The timing of crop growth stages (transplanting, tillering, heading, maturity, harvest). |
| **Block** | An Indian administrative unit below the district, spanning many villages. Current seed targeting works at this level. |
| **Extension officer / farm-advice centre** | Government staff and centres (e.g., Krishi Vigyan Kendras) that advise farmers. The intended users of the outputs. |
| **Farmer producer organisation (FPO)** | Farmer-owned groups that buy and distribute inputs like seed. |
| **Odisha** | A state on India's east coast. Study area. Its language is Odia. |
| **Bolangir, Baleswar** | The two study districts — western uplands and coastal plain respectively. |

## Remote sensing

| Term | Meaning |
|---|---|
| **SAR (synthetic aperture radar)** | A satellite sensor that sends microwaves and measures what bounces back. Works through cloud and at night. |
| **Backscatter (σ⁰)** | The strength of the returned radar signal, usually in decibels. Depends on surface roughness, structure and water content. |
| **VV, VH** | Radar polarisations — VV: sent and received vertically; VH: sent vertically, received horizontally. VH is sensitive to vegetation volume. |
| **Speckle** | Grainy noise inherent to radar images; reduced by averaging over a field. |
| **Revisit** | How often a satellite images the same place. |
| **Optical imagery** | Camera-like imagery from reflected sunlight (Sentinel-2). Blocked by cloud. |
| **NDVI** | A vegetation index from red and near-infrared reflectance; higher = greener. "Green-up" means NDVI rising. |
| **SCL** | Sentinel-2's scene classification layer: per-pixel labels for cloud, shadow, water, vegetation, etc. |
| **Reanalysis** | A gap-free reconstruction of past weather produced by combining models with observations (ERA5). |
| **Soil moisture (volumetric)** | Fraction of soil volume that is water, e.g., 0.30 = 30%. |
| **EECU** | Earth Engine compute unit — how Earth Engine measures processing for quota purposes. |
| **Embedding (AlphaEarth)** | A vector of 64 numbers summarising a pixel's surface characteristics over a year, from a pretrained model. |

## Machine learning (as used here)

| Term | Meaning |
|---|---|
| **Forecast horizon** | How far ahead a prediction is made (7, 14, 21 days before harvest). |
| **Domain adaptation / transfer** | Making a model trained in one region (source) work in another (target) with different data distribution. |
| **Zero-shot / few-shot** | Applying a model with no target labels / with a handful of target labels. |
| **Pseudo-labelling** | Using a model's confident predictions on unlabelled data as training labels. |
| **Temporal shift** | When the same crop events happen at different calendar times in different regions. |
| **Conformal prediction** | A method that turns any model's outputs into intervals with a coverage guarantee, assuming test data resemble calibration data. |
| **Coverage** | The fraction of true values that fall inside predicted intervals. |
| **PU learning** | Learning a classifier from Positive examples and Unlabelled examples (which mix positives and negatives). |
| **Class prior** | In PU learning, the fraction of unlabelled examples that are actually positive. |
| **SCAR** | "Selected completely at random" — the PU assumption that labelled positives are a random sample of all positives. Violated here. |
| **SHAP** | Shapley additive explanations — attributes a prediction to its input features. |
| **Integrated gradients** | An attribution method for neural networks that integrates gradients along a path from a baseline input. |
| **Deletion test** | Checks attribution faithfulness: removing the most-attributed inputs should hurt the model more than removing random ones. |
| **Grouped / spatial-block split** | Train/test splits where whole plots, years or regions are held out together, to avoid leakage between correlated samples. |
| **Leakage** | Information from the future or from the test set influencing training, giving over-optimistic results. |
