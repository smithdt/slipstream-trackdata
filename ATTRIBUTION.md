# Imagery attribution

Slipstream Live track imagery is derived from the public / open-licensed ortho sources below. Each carries its source's required credit; see the per-source license for terms.

- **(c) State of New South Wales (Spatial Services) - CC-BY 3.0 AU**  
  _NSW Spatial Services - NSW Imagery (data.nsw.gov.au)_
- **Connecticut ECO — UConn CLEAR & CT DEEP (2023 orthoimagery)**  
  _CT ECO 2023 statewide orthophoto (UConn CLEAR / CT DEEP), 3-inch, EPSG:3857 (probed live 2026-06-08)_
- **Contains information licensed under the Open Government Licence – Ontario**  
  _Land Information Ontario OIWMS imagery MapServer export (NOT the _Source footprints service), ~0.16 m, EPSG:3857 (probed live 2026-06-09; covers Mosport / Canadian Tire Motorsport Park)_
- **Datenquelle: basemap.at (CC BY 4.0)**  
  _basemap.at Orthofoto (bmaporthofoto30cm) WMTS google3857 XYZ tiles, 0.15-0.30 m, native EPSG:3857 (probed live 2026-06-09; host mapsneu.wien.gv.at — note {z}/{y}/{x} row/col order)_
- **FDOT — Florida Statewide Digital Orthoimagery (2020)**  
  _FDOT Statewide Yearly Aerials 2020, 3-inch, native NAD83(2011) FL East (EPSG:6439) — does NOT serve 3857 (returns black); uses the reprojection warp. Covers Sebring/Highlands (verified live 2026-06-09)._
- **Geoportale Nazionale — Ministero dell'Ambiente (MASE), Ortofoto 2012**  
  _Geoportale Nazionale (MASE) Ortofoto 2012 colore via WMS (layer OI.ORTOIMMAGINI.2012.32, UTM32N tileset), 0.50 m, EPSG:3857 — national open fallback for Italian venues outside a higher-res regional flight (e.g. Imola). NB: host forces plain HTTP._
- **Morrow County GIS — 2021 Aerial Imagery**  
  _Morrow County GIS 2021 Aerial Imagery (ImageServer, cached), ~3.7 cm, native EPSG:3857 (probed live 2026-06-12; covers Mid-Ohio Sports Car Course / ir_id 153). Also has 2014/2016/2019 vintages at same endpoint pattern._
- **NYS ITS GIS Program Office — Statewide Orthoimagery**  
  _NYS Statewide Latest Orthoimagery (ITS GIS Program Office), 6-inch source, EPSG:3857 (probed live 2026-06-08)_
- **Oregon OSIP 2018**  
  _Oregon Statewide Imagery Program OSIP 2018 (oregonexplorer.info)_
- **PNOA cedido por © Instituto Geográfico Nacional de España (CC BY 4.0)**  
  _IGN España PNOA Máxima Actualidad via WMS-INSPIRE (www.ign.es/wms-inspire/pnoa-ma, layer OI.OrthoimageCoverage), 0.25 m, EPSG:3857 (probed live 2026-06-09; covers Barcelona/Jerez/Navarra/Aragón)_
- **Texas StratMap 2019 / TxGIO (TNRIS) — Capital Area**  
  _TxGIO/TNRIS StratMap 2019 Capital Area NCCIR, 6-inch, native EPSG:3857 — drop-in (probed live 2026-06-09; covers COTA/Travis. NB: the newer StratMap21 CapArea has a nodata gap at COTA, so use 2019)._
- **USDA Farm Service Agency / USGS — public domain**  
  _USGS NAIP (USGSNAIPPlus ImageServer)_
- **Wisconsin DNR / WROC — Latest Leaf-Off Orthoimagery**  
  _WI DNR 'Latest Leaf-Off' statewide ortho (WROC), 3-inch, native EPSG:3071 — reprojects to 3857 server-side via exportImage (probed live 2026-06-09)_
- **© Digitaal Vlaanderen — Orthofotomozaïek**  
  _Digitaal Vlaanderen Orthofotomozaïek (winter, most-recent) via WMS, 0.15-0.25 m, EPSG:3857 (probed live 2026-06-09; covers Zolder — Flanders, distinct from be-wallonia/Spa)_
- **© Direção-Geral do Território (DGT) — Ortos2018 (CC BY 4.0)**  
  _DGT (Direção-Geral do Território) Ortos2018 RGB via WMS, 0.25 m, EPSG:3857 (probed live 2026-06-09; the 2021 mosaic does NOT yet cover the Algarve, the 2018 product does — use this for Portimão)_
- **© Environment Agency copyright and/or database right — Open Government Licence v3.0**  
  _Environment Agency Vertical Aerial Photography (OGL v3.0)_
- **© GeoSN (Staatsbetrieb Geobasisinformation und Vermessung Sachsen), dl-de/by-2-0**  
  _GeoSN Sachsen DOP RGB via WMS (layer sn_dop_020), 0.20 m, EPSG:3857 (probed live 2026-06-09; covers Sachsenring)_
- **© IGN — Géoplateforme (Licence Ouverte / Etalab 2.0)**  
  _IGN BD ORTHO HR via Géoplateforme WMS-R (data.geopf.fr, layer ORTHOIMAGERY.ORTHOPHOTOS)_
- **© LGL-BW, dl-de/by-2-0**  
  _LGL-BW DOP20 via INSPIRE WMS (layer OI.OrthoimageCoverage), 0.20 m, EPSG:3857 (layer confirmed via GetCapabilities 2026-06-09; covers Hockenheim. Open Data since 2024-06-09 — DOP20 only, NOT DOP10)_
- **© LVermGeo Sachsen-Anhalt, dl-de/by-2-0**  
  _LVermGeo Sachsen-Anhalt DOP20 OpenData WMS (layer lsa_lvermgeo_dop20_2), 0.20 m, EPSG:3857 (probed live 2026-06-09; covers Oschersleben — use the OpenData service, not the fee-gated GDI one)_
- **© PDOK / Kadaster — Luchtfoto Actueel (CC BY 4.0)**  
  _PDOK Luchtfoto Actueel Ortho HR (8 cm RGB) via WMS, native EPSG:28992 but serves EPSG:3857 via WMS GetMap, 0.08 m (probed live 2026-06-09; highest-res source in the set)_
- **© Prefeitura de São Paulo — GeoSampa (CC BY-SA 4.0)**  
  _GeoSampa (Prefeitura de São Paulo) Ortofoto 2020 RGB via GeoServer WMS (layer geoportal:ORTO_RGB_2020), 0.10 m, serves EPSG:3857 (probed live 2026-06-09; covers Interlagos)_
- **© Regione Emilia-Romagna — RER 2023-24 (CC BY 4.0)**  
  _Regione Emilia-Romagna RER 2023-24 RGB ortho via WMS (region's own flight, NOT the NC AGEA sibling), 0.20 m, EPSG:3857 (probed live 2026-06-09; covers Misano. NB: RER is a phased campaign — does NOT yet cover Imola, use it-mase there)_
- **© Regione Toscana — GEOscopio (CC BY 4.0)**  
  _Regione Toscana GEOscopio OFC ortho via WMS (layer rt_ofc.5k23.32bit = 2023 flight; the 2025 layer is blank at Mugello), 0.20 m, EPSG:3857 (probed live 2026-06-09; covers Mugello)_
- **© SPW (Service public de Wallonie) — open data**  
  _Wallonia ORTHO_LAST (geoservices.wallonie.be)_
- **©GeoBasis-DE / LVermGeoRP, dl-de/by-2-0 [Daten bearbeitet]**  
  _LVermGeo RLP DOP20 via WMS (layer rp_dop20), 0.20 m, EPSG:3857 (probed live 2026-06-09; covers Nürburgring GP + Nordschleife)_
- **出典：国土地理院（地理院タイル seamlessphoto を加工して作成）**  
  _GSI (Geospatial Information Authority of Japan) 地理院タイル seamlessphoto XYZ tiles, max z18 (~0.2-0.4 m effective), native EPSG:3857 (probed live 2026-06-09; nationwide — Suzuka/Fuji/Motegi/Okayama/Tsukuba)_
- **(c) Environment Agency copyright and/or database right 2019 (OGL v3.0); (c) OpenStreetMap contributors (ODbL)**  
- **(c) Scottish Government / Scottish Remote Sensing Portal (OGL v3.0); (c) OpenStreetMap contributors (ODbL)**  
