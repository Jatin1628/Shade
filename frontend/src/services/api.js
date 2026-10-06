const API_BASE = "http://127.0.0.1:8000";

export async function getWards() {
    const response = await fetch(`${API_BASE}/wards/pune`);

    if (!response.ok) {
        throw new Error("Failed to fetch Pune wards");
    }

    const data = await response.json();

    return data.features;
}

export async function getTopWards(n = 10) {
    const response = await fetch(`${API_BASE}/wards/pune/top?n=${n}`);

    if (!response.ok) {
        throw new Error("Failed to fetch top wards");
    }

    return response.json();
}

export async function getWard(wardId) {
    const response = await fetch(`${API_BASE}/wards/pune/${wardId}`);

    if (!response.ok) {
        throw new Error(`Failed to fetch ward ${wardId}`);
    }

    return response.json();
}

export async function getDataCentres() {
    const response = await fetch(`${API_BASE}/datacentres/pune`);

    if (!response.ok) {
        throw new Error("Failed to fetch data centres");
    }

    return response.json();
}