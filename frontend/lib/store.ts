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
}


interface FixtureState {
  fixtures: Record<string, Fixture>;
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
  
  getFixturesArray: () => Fixture[];
  getSortedFixtures: () => Fixture[];
}


export const useFixtureStore = create<FixtureState>()(
  persist(
    (set, get) => ({
      fixtures: {},
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
      name: "openmaritime-fixtures",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        fixtures: state.fixtures,
        lastSyncAt: state.lastSyncAt,
      }),
    }
  )
);


class CRDTSync {
  private doc: Y.Doc;
  private fixturesArray: Y.Array<Fixture>;
  private persistence: IndexeddbPersistence;
  private isInitialized = false;

  constructor() {
    this.doc = new Y.Doc();
    this.fixturesArray = this.doc.getArray<Fixture>("fixtures");
    this.persistence = new IndexeddbPersistence("openmaritime", this.doc);
  }

  async initialize() {
    if (this.isInitialized) return;

    this.persistence.on("synced", () => {
      console.log("Yjs synced with IndexedDB");
      this.isInitialized = true;
    });
  }

  getFixtures(): Fixture[] {
    return this.fixturesArray.toArray();
  }

  addFixture(fixture: Fixture) {
    this.doc.transact(() => {
      this.fixturesArray.push([fixture]);
    });
  }

  updateFixture(id: string, updates: Partial<Fixture>) {
    const index = this.fixturesArray
      .toArray()
      .findIndex((f) => f.id === id);
    if (index >= 0) {
      this.doc.transact(() => {
        const current = this.fixturesArray.get(index);
        this.fixturesArray.delete(index);
        this.fixturesArray.insert(index, [{ ...current, ...updates }]);
      });
    }
  }

  deleteFixture(id: string) {
    const index = this.fixturesArray
      .toArray()
      .findIndex((f) => f.id === id);
    if (index >= 0) {
      this.doc.transact(() => {
        this.fixturesArray.delete(index);
      });
    }
  }

  observe(callback: () => void) {
    this.fixturesArray.observe(callback);
  }

  unobserve(callback: () => void) {
    this.fixturesArray.unobserve(callback);
  }

  async syncWithServer(apiUrl: string, token: string) {
    try {
      const localFixtures = this.getFixtures();
      
      for (const fixture of localFixtures) {
        if (!fixture.isSynced) {
          const response = await fetch(`${apiUrl}/api/v1/fixtures`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(fixture),
          });

          if (response.ok) {
            this.updateFixture(fixture.id, { isSynced: true });
          }
        }
      }
    } catch (error) {
      console.error("Sync failed:", error);
      useFixtureStore.getState().setOffline(true);
    }
  }
}

export const crdtSync = new CRDTSync();
