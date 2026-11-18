import axios from "axios";

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
    timeout: 90000,
});

export const getBatters = () =>
    api.get("/rankings/batters");

export const getBowlers = () =>
    api.get("/rankings/bowlers");

export const getWeaknesses = () =>
    api.get("/rr/weaknesses");

export const getCandidates = () =>
    api.get("/auction/candidates");

export const getWatchlist = () =>
    api.get("/auction/watchlist");

export const getPlayers = () =>
    api.get("/players");

export default api;