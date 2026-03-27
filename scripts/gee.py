import ee
import geemap


def air_poll_vis(area):
    aoi = ee.Geometry.Point(area).buffer(100000)
    collection = ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2").select(
        "tropospheric_NO2_column_number_density"
    )
    recent_poll = collection.filterDate("2025-06-01", "2026-03-01").mean().clip(aoi)

    band_viz = {
        "min": 0,
        "max": 0.0002,
        "palette": ["black", "blue", "purple", "cyan", "green", "yellow", "red"],
    }

    Map = geemap.Map()
    Map.centerObject(aoi, 7)
    Map.addLayer(recent_poll, band_viz, "Recent NO2 Pollution")

    Map.to_html("air_poll_map.html")
    print("Map generated and saved to air_poll_map.html")


def temp_vis(area: list[float] = [-112.0740, 33.4484]):
    aoi = ee.Geometry.Point(area).buffer(30000)

    dataset = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterBounds(aoi)
        .filterDate("2023-06-01", "2023-08-31")
        .filter(ee.Filter.lt("CLOUD_COVER", 30))
    )

    def apply_scale_factors(image):
        thermal_band = image.select("ST_B10").multiply(0.00341802).add(149.0)
        celsius_band = thermal_band.subtract(273.15).rename("LST_Celsius")

        return image.addBands(celsius_band)

    processed_collection = dataset.map(apply_scale_factors)

    median_lst = processed_collection.select("LST_Celsius").median().clip(aoi)

    Map = geemap.Map()
    Map.centerObject(aoi, 10)

    lst_vis = {
        "min": 35.0,
        "max": 55.0,
        "palette": [
            "040274",
            "040281",
            "0502a3",
            "0502ce",
            "0502e6",
            "0602ff",  # Blues
            "307ef3",
            "269db1",
            "30c8e2",
            "32d3ef",
            "3be285",
            "3ff38f",  # Teals/Greens
            "86e26f",
            "3ae237",
            "b5e22e",
            "d6e21f",
            "fff705",
            "ffd611",  # Greens/Yellows
            "ffb613",
            "ff8b13",
            "ff6e08",
            "ff500d",
            "ff0000",
            "de0101",  # Oranges/Reds
            "c21301",
            "a71001",
            "911003",  # Dark Reds
        ],
    }

    Map.addLayer(median_lst, lst_vis, "Land Surface Temperature (C)")
    Map.to_html("lst_map.html")
    print("Map generated and saved to lst_map.html")


def main():
    ee.Authenticate()
    ee.Initialize(project="spacehack-491507")

    # Ljubljana coordinates: [Longitude, Latitude]
    air_poll_vis(area=[14.5058, 46.0569])
    temp_vis(area=[14.5058, 46.0569])


if __name__ == "__main__":
    main()
