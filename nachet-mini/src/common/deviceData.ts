import type { DeviceBrand } from "@common/types";

export const DEVICE_BRANDS: DeviceBrand[] = [
  {
    id: "tagarno",
    name: "Tagarno",
    models: [
      { id: "prestige", name: "Prestige" },
      { id: "t50", name: "T50" },
      { id: "trend", name: "Trend" },
      { id: "front", name: "Front" },
      { id: "move", name: "Move" },
      { id: "zap", name: "Zap" },
      { id: "zip", name: "Zip" },
    ],
    lenses: [
      { id: "3x", name: "3x" },
      { id: "4x", name: "4x" },
      { id: "5x", name: "5x" },
      { id: "10x", name: "10x" },
    ],
  },
];
