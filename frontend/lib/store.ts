"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import * as Y from "yjs";
import { IndexeddbPersistence } from "y-indexeddb";


export interface Fixture {
  id: string;
  vessel_name: string;
  imo_number: string | null;
  cargo_type: string;
  cargo_quantity: number;
  cargo_unit: string;
  laycan_start: string;
  laycan_end: string;
  rate: number | null;
  rate_currency: string;
  rate_unit: string;
  port_loading: string;
  port_discharge: string;
  charterer: string | null;
  broker: string | null;
  status: string;
  wake_score: number | null;
  tce_estimate: number | null;
  market_diff: number | null;
  enrichment_data: Record<string, unknown> | null;
  created_at: string;
  updated_at?: string;
  isSynced?: boolean;
  laytime_data?: LaytimeData;
  region_id?: string;
}

export interface LaytimeData {
  nor_ tendered?: string;
  nor_accepted?: string;
  loading_rate?: number;
  discharge_rate?: number;
  laytime_allowed?: number;
  laytime_used?: number;
  demurrage?: number;
  despatch?: number;
  events?: LaytimeEvent[];
}

export interface LaytimeEvent {
  id: string;
  type: "NOR" | "ARRIVAL" | "COMMENCE" | "COMPLETE" | "WEATHER";
  timestamp: string;
  description: string;
}

export interface Region {
  id: string;
  name: string;
  color: string;
  polygon?: Array<[number, number]>;
  ports?: string[];
}

export interface VoiceNote {
  id: string;
  fixture_id?: string;
  audio_blob?: Blob;
  transcript?: string;
  created_at: string;
  synced: boolean;
}

export interface EmailMessage {
  id: string;
  thread_id: string;
  subject: string;
  from: string;
  to: string;
  body: string;
  received_at: string;
  tags: string[];
  fixture_id?: string;
  is_read: boolean;
  synced: boolean;
}

export interface CostTracking {
  api_calls: Record<string, number>;
  api_costs: Record<string, number>;
  total_cost: number;
  period_start: string;
}


interface AppState {
  fixtures: Record<string, Fixture>;
  regions: Record<string, Region>;
  voiceNotes: Record<string, VoiceNote>;
  emails: Record<string, EmailMessage>;
  costTracking: CostTracking;
  selectedFixtureId: string | null;
  isOffline: boolean;
  lastSyncAt: string | null;
  
  setFixtures: (fixtures: Fixture[]) => void;
  addFixture: (fixture: Fixture) => void;
  updateFixture: (id: string, updates: Partial<Fixture>) => void;
  deleteFixture: (id: string) => void;
  selectFixture: (id: string | null) => void;
  setOffline: (offline: boolean) => void;
  setLastSyncAt: (time: string) => void;
  
  addRegion: (region: Region) => void;
  updateRegion: (id: string, updates: Partial<Region>) => void;
  deleteRegion: (id: string) => void;
  
  addVoiceNote: (note: VoiceNote) => void;
  updateVoiceNote: (id: string, updates: Partial<VoiceNote>) => void;
  
  addEmail: (email: EmailMessage) => void;
  updateEmail: (id: string, updates: Partial<EmailMessage>) => void;
  tagEmail: (id: string, tags: string[]) => void;
  
  trackApiCall: (apiName: string, cost: number) => void;
  getCostSummary: () => CostTracking;
  
  getFixturesArray: () => Fixture[];
  getSortedFixtures: () => Fixture[];
}


export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      fixtures: {},
      regions: {},
      voiceNotes: {},
      emails: {},
      costTracking: {
        api_calls: {},
        api_costs: {},
        total_cost: 0,
        period_start: new Date().toISOString(),
      },
      selectedFixtureId: null,
      isOffline: false,
      lastSyncAt: null,

      setFixtures: (fixtures) => {
        const fixtureMap: Record<string, Fixture> = {};
        fixtures.forEach((f) => {
          fixtureMap[f.id] = { ...f, isSynced: true };
        });
        set({ fixtures: fixtureMap, lastSyncAt: new Date().toISOString() });
      },

      addFixture: (fixture) => {
        set((state) => ({
          fixtures: {
            ...state.fixtures,
            [fixture.id]: { ...fixture, isSynced: false },
          },
        }));
      },

      updateFixture: (id, updates) => {
        set((state) => ({
          fixtures: {
            ...state.fixtures,
            [id]: {
              ...state.fixtures[id],
              ...updates,
              isSynced: false,
              updated_at: new Date().toISOString(),
            },
          },
        }));
      },

      deleteFixture: (id) => {
        set((state) => {
          const { [id]: _, ...rest } = state.fixtures;
          return { fixtures: rest };
        });
      },

      selectFixture: (id) => {
        set({ selectedFixtureId: id });
      },

      setOffline: (offline) => {
        set({ isOffline: offline });
      },

      setLastSyncAt: (time) => {
        set({ lastSyncAt: time });
      },

      addRegion: (region) => {
        set((state) => ({
          regions: { ...state.regions, [region.id]: region },
        }));
      },

      updateRegion: (id, updates) => {
        set((state) => ({
          regions: {
            ...state.regions,
            [id]: { ...state.regions[id], ...updates },
          },
        }));
      },

      deleteRegion: (id) => {
        set((state) => {
          const { [id]: _, ...rest } = state.regions;
          return { regions: rest };
        });
      },

      addVoiceNote: (note) => {
        set((state) => ({
          voiceNotes: { ...state.voiceNotes, [note.id]: note },
        }));
      },

      updateVoiceNote: (id, updates) => {
        set((state) => ({
          voiceNotes: {
            ...state.voiceNotes,
            [id]: { ...state.voiceNotes[id], ...updates },
          },
        }));
      },

      addEmail: (email) => {
        set((state) => ({
          emails: { ...state.emails, [email.id]: { ...email, synced: false } },
        }));
      },

      updateEmail: (id, updates) => {
        set((state) => ({
          emails: {
            ...state.emails,
            [id]: { ...state.emails[id], ...updates, synced: false },
          },
        }));
      },

      tagEmail: (id, tags) => {
        set((state) => ({
          emails: {
            ...state.emails,
            [id]: { ...state.emails[id], tags, synced: false },
          },
        }));
      },

      trackApiCall: (apiName, cost) => {
        set((state) => {
          const calls = { ...state.costTracking.api_calls };
          const costs = { ...state.costTracking.api_costs };
          calls[apiName] = (calls[apiName] || 0) + 1;
          costs[apiName] = (costs[apiName] || 0) + cost;
          const total = Object.values(costs).reduce((a, b) => a + b, 0);
          return {
            costTracking: {
              ...state.costTracking,
              api_calls: calls,
              api_costs: costs,
              total_cost: total,
            },
          };
        });
      },

      getCostSummary: () => {
        return get().costTracking;
      },

      getFixturesArray: () => {
        return Object.values(get().fixtures);
      },

      getSortedFixtures: () => {
        return Object.values(get().fixtures).sort(
          (a, b) => (b.wake_score || 0) - (a.wake_score || 0)
        );
      },
    }),
    {
      name: "openmaritime-app",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        fixtures: state.fixtures,
        regions: state.regions,
        voiceNotes: state.voiceNotes,
        emails: state.emails,
        costTracking: state.costTracking,
        lastSyncAt: state.lastSyncAt,
      }),
    }
  )
);


class CRDTSyncManager {
  private doc: Y.Doc;
  private fixturesArray: Y.Map<any>;
  private regionsArray: Y.Map<any>;
  private emailsArray: Y.Map<any>;
  private persistence: IndexeddbPersistence;
  private isInitialized = false;
  private offlineQueue: Array<{ type: string; data: any }> = [];

  constructor() {
    this.doc = new Y.Doc();
    this.fixturesArray = this.doc.getMap("fixtures");
    this.regionsArray = this.doc.getMap("regions");
    this.emailsArray = this.doc.getMap("emails");
    this.persistence = new IndexeddbPersistence("openmaritime-crdt", this.doc);
  }

  async initialize() {
    if (this.isInitialized) return;

    this.persistence.on("synced", () => {
      console.log("Yjs CRDT synced with IndexedDB");
      this.isInitialized = true;
    });

    this.fixturesArray.observe(() => this._syncToZustand());
    this.regionsArray.observe(() => this._syncToZustand());
    this.emailsArray.observe(() => this._syncToZustand());
  }

  private _syncToZustand() {
    const fixtures: Record<string, Fixture> = {};
    this.fixturesArray.forEach((value, key) => {
      fixtures[key] = value;
    });
    useAppStore.getState().setFixtures(Object.values(fixtures));

    const regions: Record<string, Region> = {};
    this.regionsArray.forEach((value, key) => {
      regions[key] = value;
    });
    Object.values(regions).forEach((r) => useAppStore.getState().addRegion(r));
  }

  addFixture(fixture: Fixture) {
    this.doc.transact(() => {
      this.fixturesArray.set(fixture.id, fixture);
    });
    this._queueOfflineAction("addFixture", fixture);
  }

  updateFixture(id: string, updates: Partial<Fixture>) {
    const existing = this.fixturesArray.get(id);
    if (existing) {
      this.doc.transact(() => {
        this.fixturesArray.set(id, { ...existing, ...updates });
      });
    }
    this._queueOfflineAction("updateFixture", { id, updates });
  }

  deleteFixture(id: string) {
    this.doc.transact(() => {
      this.fixturesArray.delete(id);
    });
    this._queueOfflineAction("deleteFixture", { id });
  }

  addRegion(region: Region) {
    this.doc.transact(() => {
      this.regionsArray.set(region.id, region);
    });
  }

  addEmail(email: EmailMessage) {
    this.doc.transact(() => {
      this.emailsArray.set(email.id, email);
    });
  }

  private _queueOfflineAction(type: string, data: any) {
    if (!navigator.onLine) {
      this.offlineQueue.push({ type, data });
    }
  }

  async syncWithServer(apiUrl: string, token: string) {
    try {
      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      };

      const fixtures = Object.values(this.fixturesArray.toJSON());
      for (const fixture of fixtures) {
        if (!fixture.isSynced) {
          await fetch(`${apiUrl}/api/v1/fixtures`, {
            method: "POST",
            headers,
            body: JSON.stringify(fixture),
          });
          this.updateFixture(fixture.id, { isSynced: true });
        }
      }

      for (const region of Object.values(this.regionsArray.toJSON())) {
        await fetch(`${apiUrl}/api/v1/regions`, {
          method: "POST",
          headers,
          body: JSON.stringify(region),
        });
      }

      useAppStore.getState().setLastSyncAt(new Date().toISOString());
      useAppStore.getState().setOffline(false);
    } catch (error) {
      console.error("CRDT sync failed:", error);
      useAppStore.getState().setOffline(true);
    }
  }

  async processOfflineQueue(apiUrl: string, token: string) {
    const queue = [...this.offlineQueue];
    this.offlineQueue = [];

    for (const action of queue) {
      try {
        await this.syncWithServer(apiUrl, token);
      } catch (e) {
        this.offlineQueue.push(action);
      }
    }
  }
}

export const crdtManager = new CRDTSyncManager();

export const useApp = useAppStore;
