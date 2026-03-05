"use client"

import { create } from "zustand"
import { Service, ServiceCategory } from "@/lib/types"

interface ServicesState {
  services: Service[]
  filterCategory: ServiceCategory | "all"
  searchQuery: string
  setServices: (services: Service[]) => void
  toggleService: (id: string, enabled: boolean) => void
  setFilterCategory: (category: ServiceCategory | "all") => void
  setSearchQuery: (query: string) => void
  filteredServices: () => Service[]
}

export const useServicesStore = create<ServicesState>((set, get) => ({
  services: [],
  filterCategory: "all",
  searchQuery: "",

  setServices: (services) => set({ services }),

  toggleService: (id, enabled) =>
    set((state) => ({
      services: state.services.map((s) =>
        s.id === id
          ? { ...s, enabledForUser: enabled, status: enabled ? "active" : "inactive" }
          : s
      ),
    })),

  setFilterCategory: (category) => set({ filterCategory: category }),
  setSearchQuery: (query) => set({ searchQuery: query }),

  filteredServices: () => {
    const { services, filterCategory, searchQuery } = get()
    return services.filter((s) => {
      const matchesCategory = filterCategory === "all" || s.category === filterCategory
      const matchesSearch =
        !searchQuery ||
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.category.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesCategory && matchesSearch
    })
  },
}))
