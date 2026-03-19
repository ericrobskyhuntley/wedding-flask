import { Map, Marker } from 'maplibre-gl';

interface EventMap {
    Slug: string;
    Lat: number;
    Lng: number;
}

document.addEventListener("DOMContentLoaded", async () => {
    const maps: EventMap[] = (window as any).MAPS;

    if (!maps || !Array.isArray(maps)) {
        console.error("MAPS data is missing or invalid");
        return;
    }
    
    maps.forEach(map => {
        const _map = new Map({
            container: `map_${map.Slug}`,
            style: 'https://api.maptiler.com/maps/39c06a26-0b36-4c9a-8467-62e0402dc331/style.json?key=TW5HwRPrq8DTWuAQ0Lmj',
            center: [map.Lng, map.Lat],
            zoom: 14,
            minZoom: 13,
            maxZoom: 20,
            maxBounds: [[-71.16394, 42.34783], [-71.0354, 42.43428]]
        });

        new Marker({
            color: "#daa520"
        }).setLngLat([map.Lng, map.Lat])
            .addTo(_map);
    })
})
