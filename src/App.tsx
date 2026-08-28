import { useState, useEffect } from 'react';
import {
  Compass,
  MapPin,
  CloudRain,
  TrendingDown,
  Lock,
  Unlock,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Search,
  User,
  Car,
  Hotel,
  Wallet,
  ShieldAlert,
  UtensilsCrossed,
  CalendarDays
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default leaflet marker icon assets in Vite
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

interface Place {
  id: string;
  name: string;
  description: string;
  lat: number;
  lng: number;
  categories: string[];
  opening_hours: { open: number; close: number };
  average_spend: number;
  duration_mins: number;
  walking_level: string;
  rating: number;
  user_ratings_total: number;
  weather_suitability: string;
}

interface ItineraryActivity {
  place: Place;
  arrival_time: string;
  departure_time: string;
  activity_cost: number;
  travel_time_mins: number;
  travel_distance_km: number;
}

interface ItineraryDay {
  day_number: number;
  activities: ItineraryActivity[];
  total_spend: number;
  total_travel_time_mins: number;
  total_walking_level: string;
}

interface ItineraryValidationReport {
  is_valid: boolean;
  budget_ok: boolean;
  time_overlap_free: boolean;
  opening_hours_ok: boolean;
  walking_limit_ok: boolean;
  warnings: string[];
}

interface Itinerary {
  version: number;
  days: ItineraryDay[];
  total_cost: number;
  total_walking_score: string;
  validity_report: ItineraryValidationReport | null;
  explanation: string;
}

interface DiffExplanation {
  before_version: number;
  after_version: number;
  changes: string[];
  reasoning: string;
}

const API_BASE = "http://localhost:8000/api";

function createMapStopIcon(label: string, tone: 'start' | 'mid' | 'end' = 'mid') {
  const palette = {
    start: { bg: '#22c55e', border: '#dcfce7', text: '#022c22' },
    mid: { bg: '#0f172a', border: '#e2e8f0', text: '#f8fafc' },
    end: { bg: '#f59e0b', border: '#fef3c7', text: '#451a03' }
  };

  const { bg, border, text } = palette[tone];

  return L.divIcon({
    className: 'travelmind-map-pin',
    html: `
      <div style="
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 9999px;
        background: ${bg};
        border: 2px solid ${border};
        box-shadow: 0 12px 18px rgba(15, 23, 42, 0.28);
        color: ${text};
        font-size: 12px;
        font-weight: 800;
        line-height: 1;
      ">${label}</div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14]
  });
}

function MapDayRoute({ points }: { points: [number, number][] }) {
  const map = useMap();

  useEffect(() => {
    if (!points.length) return;

    if (points.length === 1) {
      map.setView(points[0], 14);
      return;
    }

    const bounds = L.latLngBounds(points);
    map.fitBounds(bounds.pad(0.4), { animate: true, duration: 0.9 });
  }, [map, points]);

  return null;
}

export default function App() {
  // Application State
  const [nlQuery, setNlQuery] = useState("3 days in Munnar, Kerala, ₹12,000, history + local food + nature, balanced pace, little walking.");
  const [profile, setProfile] = useState({
    destination: "",
    state: "",
    country: "India",
    num_days: 3,
    budget: 12000,
    categories: ["history", "local food", "nature"],
    pace: "balanced",
    walking_limit: "little",
    starting_time: "09:00",
    locked_places: [] as string[]
  });
  
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [diffHistory, setDiffHistory] = useState<DiffExplanation[]>([]);
  const [activeDayTab, setActiveDayTab] = useState<number>(1);
  const [activeNavigation, setActiveNavigation] = useState<string>("overview");
  const [isParsing, setIsParsing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [serverConnected, setServerConnected] = useState(true);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [showSectionNav, setShowSectionNav] = useState(false);

  useEffect(() => {
    if (!itinerary || itinerary.days.length === 0) return;

    const hasCurrentDay = itinerary.days.some(day => day.day_number === activeDayTab);
    if (!hasCurrentDay) {
      setActiveDayTab(itinerary.days[0].day_number);
    }
  }, [itinerary, activeDayTab]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('travelmind-recent-searches');
      if (stored) {
        setRecentSearches(JSON.parse(stored));
      }
    } catch {
      setRecentSearches([]);
    }
  }, []);

  useEffect(() => {
    if (recentSearches.length) {
      localStorage.setItem('travelmind-recent-searches', JSON.stringify(recentSearches.slice(0, 6)));
    }
  }, [recentSearches]);

  // Fetch all candidate places on load to verify connection
  useEffect(() => {
    fetch(`${API_BASE}/places`)
      .then(res => {
        if (!res.ok) throw new Error("Server not responding");
        return res.json();
      })
      .then(() => {
        setServerConnected(true);
      })
      .catch(() => {
        setServerConnected(false);
      });
  }, []);

  const categoryOptions = ["history", "local food", "nature"] as const;

  const toggleCategory = (category: string) => {
    setProfile(prev => {
      const current = prev.categories.includes(category)
        ? prev.categories.filter(item => item !== category)
        : [...prev.categories, category];

      return {
        ...prev,
        categories: current.length ? current : ["history", "local food", "nature"]
      };
    });
  };

  // Parse natural language preferences
  const handleParseQuery = async () => {
    setIsParsing(true);
    setErrorMessage("");
    try {
      const res = await fetch(`${API_BASE}/parse-query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: nlQuery })
      });
      if (!res.ok) throw new Error("Failed to parse query");
      const data = await res.json();
      const nextProfile = {
        ...profile,
        destination: data.destination || "",
        state: data.state || "",
        country: data.country || "India",
        num_days: data.num_days || profile.num_days,
        budget: data.budget || profile.budget,
        categories: data.categories?.length ? data.categories : profile.categories,
        pace: data.pace || profile.pace,
        walking_limit: data.walking_limit || profile.walking_limit,
        starting_time: data.starting_time || profile.starting_time
      };

      setProfile(nextProfile);
      setActiveNavigation("overview");
      saveRecentSearch(nlQuery);

      if (!data.destination || !data.destination.trim()) {
        setErrorMessage("Where in India would you like to travel?");
        return;
      }

      await handleGenerateItinerary(nextProfile);
    } catch (err: any) {
      setErrorMessage(err.message || "Error communicating with server.");
    } finally {
      setIsParsing(false);
    }
  };

  // Generate original itinerary
  const handleGenerateItinerary = async (currentProfile = profile) => {
    if (!currentProfile.destination || !currentProfile.destination.trim()) {
      setErrorMessage("Please choose a destination in India.");
      return;
    }

    setIsGenerating(true);
    setErrorMessage("");
    try {
      const res = await fetch(`${API_BASE}/generate-itinerary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(currentProfile)
      });
      if (!res.ok) throw new Error("Failed to generate itinerary");
      const data = await res.json();
      setItinerary(data);
      setDiffHistory([]);
      setActiveDayTab(1);
    } catch (err: any) {
      setErrorMessage(err.message || "Error generating itinerary.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Trigger Adaptive Re-plan
  const handleReplan = async (trigger: string, value?: string) => {
    if (!itinerary) return;
    setErrorMessage("");
    try {
      const res = await fetch(`${API_BASE}/replan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_itinerary: itinerary,
          profile: profile,
          trigger: trigger,
          trigger_value: value
        })
      });
      if (!res.ok) throw new Error("Re-planning request failed");
      const data = await res.json();
      setItinerary(data.itinerary);
      setDiffHistory(prev => [data.diff, ...prev]);
      setActiveNavigation("replan");

      // Update local profile representation
      if (trigger === "rain") {
        // Rain is simulated internally by filtering outdoor
      } else if (trigger === "budget_cut") {
        setProfile(prev => ({ ...prev, budget: prev.budget * 0.7 }));
      } else if (trigger === "less_walking") {
        setProfile(prev => ({ ...prev, walking_limit: "little" }));
      } else if (trigger === "later_start") {
        setProfile(prev => ({ ...prev, starting_time: "11:00" }));
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Error during re-planning.");
    }
  };

  // Add place lock toggle
  const toggleLockPlace = (placeId: string) => {
    const updatedLocked = profile.locked_places.includes(placeId)
      ? profile.locked_places.filter(id => id !== placeId)
      : [...profile.locked_places, placeId];
    
    const updatedProfile = { ...profile, locked_places: updatedLocked };
    setProfile(updatedProfile);
    if (itinerary) {
      handleGenerateItinerary(updatedProfile);
    }
  };

  // Remove place from current schedule (uses blacklist replan trigger)
  const handleRemovePlace = (placeId: string) => {
    handleReplan("close_place", placeId);
  };

  // Pre-load Demo query
  const loadDemoQuery = () => {
    setNlQuery("3 days in Munnar, Kerala, ₹12,000, history + local food + nature, balanced pace, little walking.");
  };

  // Get the real selected itinerary day and keep the UI consistent with the generated plan.
  const selectedDay = itinerary?.days.find(d => d.day_number === activeDayTab) ?? itinerary?.days[0] ?? null;
  const activeDayActivities = selectedDay?.activities || [];
  const routePoints = activeDayActivities.map(act => [act.place.lat, act.place.lng] as [number, number]);

  // Center coordinate of map is set to active day's first place, or central India
  const mapCenter = routePoints.length > 0 ? routePoints[0] : [22.9734, 78.6569] as [number, number];

  const navigationItems = [
    { key: "overview", label: "Overview", icon: Compass },
    { key: "itinerary", label: "Itinerary", icon: CalendarDays },
    { key: "places", label: "Places", icon: MapPin },
    { key: "food", label: "Food", icon: UtensilsCrossed },
    { key: "hotels", label: "Hotels", icon: Hotel },
    { key: "transport", label: "Transport", icon: Car },
    { key: "budget", label: "Budget", icon: Wallet },
    { key: "weather", label: "Weather", icon: CloudRain },
    { key: "profile", label: "Profile", icon: User },
    { key: "replan", label: "Re-plan", icon: TrendingDown },
    { key: "emergency", label: "Emergency", icon: ShieldAlert }
  ];

  const overviewNextActivity = selectedDay?.activities?.[0] ?? null;
  const placesPanel = itinerary ? itinerary.days.flatMap(day => day.activities.map(act => act.place)) : [];
  const foodPanel = placesPanel.filter(place => place.categories.includes("local food"));

  const saveRecentSearch = (searchText: string) => {
    const trimmed = searchText.trim();
    if (!trimmed) return;
    setRecentSearches(prev => {
      const deduped = prev.filter(item => item.toLowerCase() !== trimmed.toLowerCase());
      return [trimmed, ...deduped].slice(0, 6);
    });
  };

  const renderSelectedPanel = () => {
    if (activeNavigation === "overview") {
      return (
        <div className="p-5 space-y-4">
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3">
            <p className="text-[10px] uppercase tracking-[0.18em] text-emerald-300">I understood your trip as</p>
            <div className="mt-2 space-y-1 text-xs text-slate-100">
              <p><span className="text-slate-400">📍</span> {profile.destination || 'Not specified'}</p>
              <p><span className="text-slate-400">📅</span> {profile.num_days || 3} Days</p>
              <p><span className="text-slate-400">💰</span> ₹{(profile.budget || 12000).toLocaleString('en-IN')}</p>
              <p><span className="text-slate-400">👨‍👩‍👧</span> {profile.categories.join(', ') || 'General trip'}</p>
            </div>
            <button
              onClick={() => setActiveNavigation("profile")}
              className="mt-3 w-full rounded-lg border border-emerald-500/30 bg-slate-950 px-2.5 py-1.5 text-[10px] font-semibold text-emerald-300"
            >
              Edit Profile
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-400">Destination</p>
              <h2 className="text-xl font-bold text-white mt-1">{profile.destination || "Choose a destination"}</h2>
            </div>
            <button
              onClick={() => setActiveNavigation("profile")}
              className="px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-xs text-slate-200"
            >
              Edit
            </button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Trip duration</p>
              <p className="mt-2 text-lg font-bold text-white">{profile.num_days || 3} days</p>
            </div>
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Budget</p>
              <p className="mt-2 text-lg font-bold text-white">₹{(profile.budget || 12000).toLocaleString('en-IN')}</p>
            </div>
          </div>

          {itinerary && itinerary.days.length > 0 && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Days</p>
              <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
                {itinerary.days.map(day => (
                  <button
                    key={day.day_number}
                    type="button"
                    onClick={() => setActiveDayTab(day.day_number)}
                    className={`shrink-0 rounded-lg border px-2.5 py-1.5 text-[10px] font-semibold ${activeDayTab === day.day_number ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-slate-700 bg-slate-950 text-slate-300'}`}
                  >
                    Day {day.day_number}
                  </button>
                ))}
              </div>
              <div className="mt-3 space-y-2">
                {(selectedDay?.activities || []).map((act, index) => (
                  <div key={`${act.place.id}-${index}`} className="rounded-lg border border-slate-700 bg-slate-950/80 p-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-white">{act.place.name}</p>
                      <span className="text-[9px] text-emerald-300">₹{Math.round(act.activity_cost)}</span>
                    </div>
                    <p className="mt-1 text-[10px] text-slate-400">{act.arrival_time} - {act.departure_time}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!itinerary && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <p className="text-slate-400 text-xs uppercase tracking-[0.2em]">Today</p>
                <span className="text-xs text-emerald-300">Day {activeDayTab}</span>
              </div>
              <p className="mt-3 text-white font-semibold">No activity scheduled yet</p>
              <p className="text-xs text-slate-400 mt-1">Plan your route to begin</p>
            </div>
          )}

          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
            <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Weather</p>
            <div className="mt-2 flex items-center justify-between">
              <div>
                <p className="text-xl font-bold text-white">24°C</p>
                <p className="text-xs text-slate-400">Partly cloudy • 18% rain</p>
              </div>
              <CloudRain className="w-8 h-8 text-emerald-400" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
              <div className="flex items-center gap-2 text-emerald-300">
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-[10px] uppercase tracking-[0.18em]">Status</span>
              </div>
              <p className="mt-2 text-sm font-bold text-white">Ready</p>
            </div>
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
              <div className="flex items-center gap-2 text-amber-300">
                <Layers className="h-4 w-4" />
                <span className="text-[10px] uppercase tracking-[0.18em]">Route</span>
              </div>
              <p className="mt-2 text-sm font-bold text-white">Live</p>
            </div>
          </div>

          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
            <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Remaining budget</p>
            <p className="mt-2 text-xl font-bold text-white">₹{Math.max(0, (profile.budget || 12000) - (itinerary?.total_cost || 0)).toLocaleString('en-IN')}</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => setActiveNavigation("itinerary")} className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-3 py-2 rounded-xl text-xs">View Itinerary</button>
            <button onClick={() => setActiveNavigation("places")} className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs border border-slate-700">Places Nearby</button>
            <button onClick={() => { setShowSectionNav(true); setActiveNavigation("replan"); }} className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs border border-slate-700">Re-plan</button>
            <button
              onClick={() => handleGenerateItinerary()}
              disabled={isGenerating}
              className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs border border-slate-700 disabled:opacity-60"
            >
              {isGenerating ? 'Planning...' : 'Navigate'}
            </button>
          </div>

          {!showSectionNav && (
            <button
              onClick={() => setShowSectionNav(true)}
              className="w-full rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-300"
            >
              Need to change something?
            </button>
          )}
        </div>
      );
    }

    if (activeNavigation === "itinerary") {
      return (
        <div className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-white">Itinerary</h3>
            <span className="text-xs text-emerald-300">{itinerary?.days.length || 0} days</span>
          </div>

          <div className="flex gap-2 overflow-x-auto pb-1">
            {['Timeline', 'Feasibility & Budget', 'Adaptive Re-plan (1)'].map((tab, index) => (
              <button
                key={tab}
                className={`shrink-0 rounded-full border px-2.5 py-1.5 text-[10px] font-medium ${index === 0 ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-slate-700 bg-slate-800 text-slate-300'}`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="flex gap-2 overflow-x-auto pb-1">
            {itinerary?.days.map(day => (
              <button
                key={day.day_number}
                onClick={() => setActiveDayTab(day.day_number)}
                className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold ${activeDayTab === day.day_number ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-300 border border-slate-700"}`}
              >
                Day {day.day_number}
              </button>
            ))}
          </div>

          {selectedDay && (
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Day {selectedDay.day_number}</p>
                  <p className="mt-1 text-sm font-bold text-white">{selectedDay.activities.length} planned stops</p>
                </div>
                <div className="text-right text-[10px] text-emerald-300">
                  <div>₹{Math.round(selectedDay.total_spend).toLocaleString('en-IN')}</div>
                  <div className="mt-1 text-slate-400">{selectedDay.total_walking_level} walk</div>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-3">
            {(selectedDay?.activities || []).map((act, index) => (
              <div key={`${act.place.id}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 shadow-lg shadow-slate-950/20">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2">
                    <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/15 text-[10px] font-bold text-emerald-300 border border-emerald-500/30">
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-white">{act.place.name}</p>
                      <p className="text-[11px] text-slate-400">{act.arrival_time} - {act.departure_time}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold text-emerald-300">₹{Math.round(act.activity_cost)}</span>
                    <button
                      onClick={() => toggleLockPlace(act.place.id)}
                      className="rounded border border-slate-700 bg-slate-800 p-1.5 text-slate-300 hover:text-emerald-300"
                      title="Lock this place"
                    >
                      {profile.locked_places.includes(act.place.id) ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
                    </button>
                    <button
                      onClick={() => handleRemovePlace(act.place.id)}
                      className="rounded border border-slate-700 bg-slate-800 p-1.5 text-slate-300 hover:text-rose-300"
                      title="Remove this place"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                <p className="mt-3 text-[11px] leading-5 text-slate-300">{act.place.description}</p>

                <div className="mt-3 grid grid-cols-3 gap-2 text-[10px] text-slate-300">
                  <div className="rounded-lg border border-slate-700 bg-slate-950/80 p-2">
                    <p className="text-slate-400">Time</p>
                    <p className="mt-1 font-semibold text-white">{act.arrival_time} - {act.departure_time}</p>
                  </div>
                  <div className="rounded-lg border border-slate-700 bg-slate-950/80 p-2">
                    <p className="text-slate-400">Cost</p>
                    <p className="mt-1 font-semibold text-white">₹{Math.round(act.activity_cost)}</p>
                  </div>
                  <div className="rounded-lg border border-slate-700 bg-slate-950/80 p-2">
                    <p className="text-slate-400">Walk</p>
                    <p className="mt-1 font-semibold text-white">{act.place.walking_level}</p>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-2 text-[10px] text-emerald-200">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    Travel: {act.travel_time_mins} mins
                  </span>
                  <span>{act.travel_distance_km.toFixed(1)} km</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (activeNavigation === "places") {
      return (
        <div className="p-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Places</h3>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {['Popular', 'Nature', 'History', 'Adventure', 'Family', 'Hidden Gems'].map(tag => (
              <button key={tag} className="whitespace-nowrap rounded-full bg-slate-800 text-slate-200 border border-slate-700 px-3 py-1.5 text-[11px]">{tag}</button>
            ))}
          </div>
          <div className="space-y-3">
            {placesPanel.slice(0, 8).map((place, index) => (
              <div key={`${place.id}-${index}`} className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-bold text-white">{place.name}</p>
                    <p className="text-[11px] text-slate-400">{place.description}</p>
                  </div>
                  <button className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-1 rounded-lg text-[10px]">Add</button>
                </div>
                <div className="mt-3 flex justify-between text-[10px] text-slate-300">
                  <span>{place.walking_level} walk</span>
                  <span>₹{place.average_spend}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (activeNavigation === "food") {
      return (
        <div className="p-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Food</h3>
          <div className="space-y-3">
            {foodPanel.length ? foodPanel.slice(0, 6).map((place, index) => (
              <div key={`${place.id}-food-${index}`} className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-bold text-white">{place.name}</p>
                  <span className="text-[10px] text-emerald-300">⭐ 4.6</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">Local food • ₹{place.average_spend}</p>
              </div>
            )) : (
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 text-sm text-slate-300">
                No local food stops found for this destination yet.
              </div>
            )}
          </div>
        </div>
      );
    }

    if (activeNavigation === "hotels") {
      return (
        <div className="p-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Hotels</h3>
          <div className="space-y-3">
            {[{ name: 'Stay near destination', price: '₹2,400/night', rating: '4.7', amenity: 'Free parking + breakfast' }, { name: 'Boutique hill stay', price: '₹3,200/night', rating: '4.5', amenity: 'Mountain view' }, { name: 'Budget lodge', price: '₹1,600/night', rating: '4.3', amenity: 'Local shuttle' }].map((hotel) => (
              <div key={hotel.name} className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-bold text-white">{hotel.name}</p>
                  <span className="text-[10px] text-emerald-300">⭐ {hotel.rating}</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">{hotel.price} • {hotel.amenity}</p>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (activeNavigation === "transport") {
      return (
        <div className="p-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Transport</h3>
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-2 text-sm text-slate-200">
            <div className="flex justify-between"><span>Current location</span><span>India</span></div>
            <div className="flex justify-between"><span>Destination</span><span>{profile.destination || 'Not selected'}</span></div>
            <div className="flex justify-between"><span>Taxi</span><span>₹1,200</span></div>
            <div className="flex justify-between"><span>Bus</span><span>₹350</span></div>
            <div className="flex justify-between"><span>Train</span><span>₹780</span></div>
          </div>
        </div>
      );
    }

    if (activeNavigation === "budget") {
      return (
        <div className="p-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Budget</h3>
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
            <div className="flex justify-between text-xs text-slate-400"><span>Total budget</span><span>₹{(profile.budget || 12000).toLocaleString('en-IN')}</span></div>
            <div className="mt-4 h-2.5 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, ((itinerary?.total_cost || 0) / (profile.budget || 12000)) * 100)}%` }} />
            </div>
            <div className="mt-3 space-y-2 text-sm text-slate-200">
              <div className="flex justify-between"><span>Accommodation</span><span>₹{Math.round((itinerary?.total_cost || 0) * 0.45).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between"><span>Food</span><span>₹{Math.round((itinerary?.total_cost || 0) * 0.2).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between"><span>Transport</span><span>₹{Math.round((itinerary?.total_cost || 0) * 0.15).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between"><span>Entry fees</span><span>₹{Math.round((itinerary?.total_cost || 0) * 0.1).toLocaleString('en-IN')}</span></div>
              <div className="flex justify-between font-bold text-white"><span>Total estimated</span><span>₹{(itinerary?.total_cost || 0).toLocaleString('en-IN')}</span></div>
            </div>
          </div>
        </div>
      );
    }

    if (activeNavigation === "weather") {
      return (
        <div className="p-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Weather</h3>
          <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xl font-bold text-white">24°C</p>
                <p className="text-xs text-slate-400">Partly cloudy</p>
              </div>
              <CloudRain className="w-8 h-8 text-emerald-400" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-[10px] text-slate-300">
              <div className="bg-slate-800 rounded-lg p-2"><p>Mon</p><p className="text-white mt-1">26°C</p></div>
              <div className="bg-slate-800 rounded-lg p-2"><p>Tue</p><p className="text-white mt-1">23°C</p></div>
              <div className="bg-slate-800 rounded-lg p-2"><p>Wed</p><p className="text-white mt-1">22°C</p></div>
            </div>
          </div>
        </div>
      );
    }

    if (activeNavigation === "profile") {
      return (
        <div className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-white">Traveler Profile</h3>
            <button onClick={() => handleGenerateItinerary()} className="bg-emerald-600 text-slate-950 px-3 py-1.5 rounded-lg text-xs font-bold">Apply</button>
          </div>

          <div className="space-y-3">
            <label className="block text-xs text-slate-300">Destination</label>
            <input
              value={profile.destination}
              onChange={(e) => setProfile({ ...profile, destination: e.target.value })}
              placeholder="Type any Indian destination"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200 placeholder:text-slate-500"
            />
            <label className="block text-xs text-slate-300">State</label>
            <input
              value={profile.state}
              onChange={(e) => setProfile({ ...profile, state: e.target.value })}
              placeholder="State or union territory"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200 placeholder:text-slate-500"
            />
            <label className="block text-xs text-slate-300">Duration</label>
            <input type="number" value={profile.num_days} onChange={(e) => setProfile({ ...profile, num_days: parseInt(e.target.value) || 3 })} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" />
            <label className="block text-xs text-slate-300">Budget</label>
            <input type="number" value={profile.budget} onChange={(e) => setProfile({ ...profile, budget: parseFloat(e.target.value) || 12000 })} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" />
            <label className="block text-xs text-slate-300">Start time</label>
            <input type="time" value={profile.starting_time} onChange={(e) => setProfile({ ...profile, starting_time: e.target.value })} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200" />
            <label className="block text-xs text-slate-300">Interests</label>
            <div className="flex flex-wrap gap-2">
              {categoryOptions.map(category => (
                <button
                  key={category}
                  type="button"
                  onClick={() => toggleCategory(category)}
                  className={`rounded-full border px-2.5 py-1.5 text-[10px] font-medium ${profile.categories.includes(category) ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' : 'border-slate-700 bg-slate-800 text-slate-300'}`}
                >
                  {category}
                </button>
              ))}
            </div>
            <label className="block text-xs text-slate-300">Activity Pace</label>
            <select value={profile.pace} onChange={(e) => setProfile({ ...profile, pace: e.target.value })} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200">
              <option value="slow">Slow</option>
              <option value="balanced">Balanced</option>
              <option value="fast">Fast</option>
            </select>
            <label className="block text-xs text-slate-300">Walking</label>
            <select value={profile.walking_limit} onChange={(e) => setProfile({ ...profile, walking_limit: e.target.value })} className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200">
              <option value="little">Little</option>
              <option value="moderate">Moderate</option>
              <option value="active">Active</option>
            </select>
          </div>
        </div>
      );
    }

    if (activeNavigation === "replan") {
      return (
        <div className="p-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Adaptive Re-plan</h3>
          <div className="grid grid-cols-2 gap-3">
            {['Budget Changed', 'Weather Changed', 'Attraction Closed', 'Too Much Walking', 'Running Late', 'Need Rest', 'Skip Activity', 'Change Duration'].map(option => (
              <button key={option} onClick={() => handleReplan(option.toLowerCase().replace(/ /g, '_'))} className="bg-slate-800 border border-slate-700 rounded-xl p-3 text-[11px] text-slate-200 hover:border-emerald-500/50">{option}</button>
            ))}
          </div>
          {diffHistory.length > 0 ? <div className="space-y-2">{diffHistory.slice(0, 2).map((diff, index) => <div key={index} className="bg-slate-900/70 border border-slate-800 rounded-xl p-3 text-xs text-slate-300">{diff.reasoning}</div>)}</div> : <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3 text-xs text-slate-300">No re-plan updates yet.</div>}
        </div>
      );
    }

    return (
      <div className="p-5 space-y-4">
        <h3 className="text-lg font-bold text-white">Emergency</h3>
        <div className="space-y-3">
          {['Nearby Hospital', 'Police', 'Pharmacy', 'Travel Assistance'].map((item) => (
            <div key={item} className="bg-slate-900/70 border border-slate-800 rounded-xl p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-white">{item}</p>
                <ShieldAlert className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">Operational support in the destination area.</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-950 text-slate-100">
      <aside className="w-[360px] min-w-[300px] shrink-0 overflow-y-auto border-r border-slate-800 bg-slate-950/95 p-3">
        <div className="space-y-3">
          <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-slate-950 font-black">
              <Compass className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-black tracking-tight text-white">TravelMind</p>
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Trip planner</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
            <div className="mb-2 flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-2">
              <Search className="h-3.5 w-3.5 text-slate-400" />
              <input
                value={nlQuery}
                onChange={(e) => setNlQuery(e.target.value)}
                onKeyDown={async (e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (!nlQuery.trim()) {
                      setErrorMessage('Describe your trip to start planning.');
                      return;
                    }
                    saveRecentSearch(nlQuery);
                    await handleParseQuery();
                  }
                }}
                placeholder="Describe your trip"
                className="w-full bg-transparent text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none"
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={async () => {
                  if (!nlQuery.trim()) {
                    setErrorMessage('Describe your trip to start planning.');
                    return;
                  }
                  saveRecentSearch(nlQuery);
                  await handleParseQuery();
                }}
                disabled={isParsing || !nlQuery}
                className="flex-1 rounded-xl bg-emerald-600 px-3 py-2 text-[11px] font-bold text-slate-950 transition hover:bg-emerald-500 disabled:opacity-50"
              >
                {isParsing ? '...' : 'Plan Trip'}
              </button>
              <button
                onClick={loadDemoQuery}
                className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-[11px] font-medium text-slate-200"
              >
                Demo
              </button>
            </div>
          </div>

          {errorMessage && (
            <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">
              <AlertTriangle className="h-3.5 w-3.5" />
              {errorMessage}
            </div>
          )}

          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Recent Searches</p>
              <span className="text-[9px] text-slate-400">{recentSearches.length}</span>
            </div>
            <div className="space-y-2">
              {recentSearches.length ? recentSearches.map((item, idx) => (
                <button
                  key={`${item}-${idx}`}
                  onClick={async () => {
                    setNlQuery(item);
                    setActiveNavigation('overview');
                    await handleParseQuery();
                  }}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-2 text-left text-[10px] text-slate-300 hover:border-emerald-500/30 hover:text-emerald-300"
                >
                  {item}
                </button>
              )) : (
                <div className="rounded-xl border border-slate-700 bg-slate-950 px-2.5 py-2 text-[10px] text-slate-400">
                  No recent plans yet.
                </div>
              )}
            </div>
          </div>

          {showSectionNav && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">Sections</p>
                <span className={`inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[9px] font-semibold text-emerald-300`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${serverConnected ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                  {serverConnected ? 'Live' : 'Offline'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {navigationItems.map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    onClick={() => setActiveNavigation(key)}
                    className={`flex items-center justify-between rounded-xl border px-2.5 py-2 text-left text-[10px] font-medium transition ${
                      activeNavigation === key
                        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                        : 'border-slate-700 bg-slate-950 text-slate-200'
                    }`}
                  >
                    <span>{label}</span>
                    <Icon className="h-3.5 w-3.5" />
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3">
            {renderSelectedPanel()}
          </div>
        </div>
      </aside>

      <main className="relative flex-1 min-w-0 bg-slate-950">
        <MapContainer
          center={mapCenter}
          zoom={12}
          scrollWheelZoom={false}
          zoomControl={true}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapDayRoute points={routePoints} />

          {activeDayActivities.map((act, index) => {
            const tone = index === 0 ? 'start' : index === activeDayActivities.length - 1 ? 'end' : 'mid';

            return (
              <Marker
                key={`${act.place.id}-${index}`}
                position={[act.place.lat, act.place.lng]}
                icon={createMapStopIcon(String(index + 1), tone)}
              >
                <Popup>
                  <div className="text-xs">
                    <strong className="text-white block font-bold mb-0.5">{index + 1}. {act.place.name}</strong>
                    <span className="text-slate-400 block mb-1">{act.arrival_time} - {act.departure_time}</span>
                    <span className="text-slate-300">₹{act.activity_cost}</span>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {routePoints.length > 1 && (
            <Polyline
              positions={routePoints}
              color="#22c55e"
              weight={5}
              opacity={0.95}
              lineCap="round"
              lineJoin="round"
              dashArray="10, 10"
            />
          )}
        </MapContainer>

        <div className="pointer-events-none absolute left-4 top-4 rounded-2xl border border-slate-700 bg-slate-900/85 p-4 shadow-xl backdrop-blur-md">
          <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Selected destination</p>
          <h3 className="mt-1 text-lg font-bold text-white">{profile.destination || 'Choose a destination'}</h3>
          <div className="mt-2 flex gap-3 text-[11px] text-slate-300">
            <span>{profile.num_days || 3} days</span>
            <span>₹{(profile.budget || 12000).toLocaleString('en-IN')}</span>
          </div>
        </div>

        {itinerary && (
          <div className="pointer-events-none absolute bottom-4 left-4 rounded-2xl border border-slate-700 bg-slate-900/85 p-3 shadow-xl backdrop-blur-md">
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Next stop</p>
            <p className="mt-1 text-sm font-bold text-white">{overviewNextActivity?.place.name || 'Ready to plan'}</p>
            <p className="text-[11px] text-slate-300">{overviewNextActivity ? `${overviewNextActivity.arrival_time} • ${overviewNextActivity.place.walking_level} walk` : 'Update itinerary'}</p>
          </div>
        )}
      </main>
    </div>
  );
}