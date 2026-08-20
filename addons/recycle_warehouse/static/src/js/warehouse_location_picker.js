/** @odoo-module **/

import { Component, useRef, onMounted, onWillUnmount, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Pick a warehouse's location on an interactive map instead of typing two
 * numbers by hand.
 *
 * Free and key-less on purpose: the tiles come from OpenStreetMap and the map
 * engine is Leaflet, both vendored into this addon (static/lib/leaflet) — there
 * is no Google Maps API key, no billing account and no external script to
 * whitelist. The admin clicks the map (or drags the marker) and the two
 * coordinate fields fill themselves; the fields stay on the form too, so a known
 * pair can still be typed and the map follows.
 *
 * Bound to the `latitude` field but writes BOTH `latitude` and `longitude` on
 * the record — a location is one decision, not two independent numbers.
 */
export class WarehouseLocationPicker extends Component {
    static template = "recycle_warehouse.WarehouseLocationPicker";
    static props = { ...standardFieldProps };

    setup() {
        this.mapRef = useRef("map");
        this.map = null;
        this.marker = null;
        onMounted(() => this._initMap());
        // The other field (longitude) or an external write can move the point
        // while the widget is mounted — keep the marker in step with the record.
        onWillUpdateProps((nextProps) => this._syncFromRecord(nextProps.record));
        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
                this.map = null;
            }
        });
    }

    get record() {
        return this.props.record;
    }

    get isReadonly() {
        return this.props.readonly;
    }

    /** Current pair, falling back to a sensible default centre (Damascus, SY). */
    _currentLatLng(record = this.record) {
        const lat = record.data.latitude;
        const lng = record.data.longitude;
        const hasPoint = Number.isFinite(lat) && Number.isFinite(lng) && (lat || lng);
        return {
            lat: hasPoint ? lat : 33.5138,
            lng: hasPoint ? lng : 36.2765,
            hasPoint,
        };
    }

    _initMap() {
        const L = window.L;
        if (!L || !this.mapRef.el) {
            return;
        }
        const { lat, lng, hasPoint } = this._currentLatLng();
        this.map = L.map(this.mapRef.el).setView([lat, lng], hasPoint ? 14 : 6);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "© OpenStreetMap contributors",
        }).addTo(this.map);

        // A RED teardrop pin marks the picked spot — drawn as an inline SVG so it
        // needs no image file and reads instantly as "the warehouse is here".
        const redPin = L.divIcon({
            className: "o_recycle_redpin",
            html: '<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg"><path d="M14 0C6.27 0 0 6.27 0 14c0 10.5 14 26 14 26s14-15.5 14-26C28 6.27 21.73 0 14 0z" fill="#dc2626" stroke="#991b1b" stroke-width="1"/><circle cx="14" cy="14" r="5.5" fill="#ffffff"/></svg>',
            iconSize: [28, 40],
            iconAnchor: [14, 40],
        });
        this.marker = L.marker([lat, lng], { draggable: !this.isReadonly, icon: redPin }).addTo(this.map);

        if (!this.isReadonly) {
            this.marker.on("dragend", () => this._commit(this.marker.getLatLng()));
            this.map.on("click", (ev) => {
                this.marker.setLatLng(ev.latlng);
                this._commit(ev.latlng);
            });
        }

        // The form often renders the map in a not-yet-sized container (inside a
        // group/notebook); Leaflet needs a nudge once the layout settles or it
        // paints a grey box with tiles only in the top-left corner.
        setTimeout(() => this.map && this.map.invalidateSize(), 250);
    }

    /** Move the marker when the record's coordinates change from elsewhere. */
    _syncFromRecord(record) {
        if (!this.map || !this.marker) {
            return;
        }
        const { lat, lng, hasPoint } = this._currentLatLng(record);
        const here = this.marker.getLatLng();
        if (hasPoint && (Math.abs(here.lat - lat) > 1e-9 || Math.abs(here.lng - lng) > 1e-9)) {
            this.marker.setLatLng([lat, lng]);
            this.map.panTo([lat, lng]);
        }
    }

    /** Write the picked point back to BOTH coordinate fields, rounded to 7 dp. */
    _commit(latlng) {
        this.record.update({
            latitude: Number(latlng.lat.toFixed(7)),
            longitude: Number(latlng.lng.toFixed(7)),
        });
    }
}

export const warehouseLocationPicker = {
    component: WarehouseLocationPicker,
    supportedTypes: ["float"],
};

registry.category("fields").add("warehouse_location_picker", warehouseLocationPicker);
