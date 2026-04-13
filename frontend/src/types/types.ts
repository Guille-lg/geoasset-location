export interface Company {
  id: string
  name: string
  address?: string
  types?: string[]
  website?: string
  cif?: string
  sector?: string
  cnae?: string
  logo_url?: string
  headquarters?: string
}

export enum AssetCategory {
  HQ = 'HQ',
  OFF = 'OFF',
  FAB = 'FAB',
  LOG = 'LOG',
  TEC = 'TEC',
  COM = 'COM',
  AGR = 'AGR',
  ENE = 'ENE',
  TRA = 'TRA',
  HOT = 'HOT',
  SAN = 'SAN',
  OTR = 'OTR',
}

export const CATEGORY_LABELS: Record<AssetCategory, string> = {
  [AssetCategory.HQ]: 'Sede Central',
  [AssetCategory.OFF]: 'Oficina Regional',
  [AssetCategory.FAB]: 'Fábrica / Planta',
  [AssetCategory.LOG]: 'Centro Logístico',
  [AssetCategory.TEC]: 'Centro Tecnológico',
  [AssetCategory.COM]: 'Punto de Venta',
  [AssetCategory.AGR]: 'Explotación Agrícola',
  [AssetCategory.ENE]: 'Inst. Energética',
  [AssetCategory.TRA]: 'Infraestructura Transporte',
  [AssetCategory.HOT]: 'Activo Hotelero',
  [AssetCategory.SAN]: 'Centro Sanitario',
  [AssetCategory.OTR]: 'Otro',
}

export const CATEGORY_ICONS: Record<AssetCategory, string> = {
  [AssetCategory.HQ]: 'mdi-office-building',
  [AssetCategory.OFF]: 'mdi-domain',
  [AssetCategory.FAB]: 'mdi-factory',
  [AssetCategory.LOG]: 'mdi-warehouse',
  [AssetCategory.TEC]: 'mdi-flask',
  [AssetCategory.COM]: 'mdi-store',
  [AssetCategory.AGR]: 'mdi-sprout',
  [AssetCategory.ENE]: 'mdi-lightning-bolt',
  [AssetCategory.TRA]: 'mdi-train',
  [AssetCategory.HOT]: 'mdi-bed',
  [AssetCategory.SAN]: 'mdi-hospital-box',
  [AssetCategory.OTR]: 'mdi-map-marker',
}

export const CATEGORY_COLORS: Record<AssetCategory, string> = {
  [AssetCategory.HQ]: '#1565C0',
  [AssetCategory.OFF]: '#2196F3',
  [AssetCategory.FAB]: '#E65100',
  [AssetCategory.LOG]: '#FF9800',
  [AssetCategory.TEC]: '#7B1FA2',
  [AssetCategory.COM]: '#4CAF50',
  [AssetCategory.AGR]: '#33691E',
  [AssetCategory.ENE]: '#FDD835',
  [AssetCategory.TRA]: '#607D8B',
  [AssetCategory.HOT]: '#E91E63',
  [AssetCategory.SAN]: '#F44336',
  [AssetCategory.OTR]: '#9E9E9E',
}

export interface Asset {
  id: string
  company_id: string
  name: string
  raw_name: string
  category: AssetCategory
  subcategory?: string
  latitude: number
  longitude: number
  address: string
  municipality: string
  province: string
  autonomous_community: string
  postal_code?: string
  description?: string
  size_estimate?: string
  functional_tags: string[]
  is_headquarters: boolean
  google_place_id: string
  confidence_score: number
  confidence_tier: string
  data_sources: string[]
  website?: string
  phone?: string
  created_at?: string
  updated_at?: string
}

export interface PipelineStep {
  step: number
  name: string
  status: 'pending' | 'running' | 'complete' | 'error'
  estimated_seconds?: number
  found?: number
  error?: string
}

export interface AnalysisMetadata {
  company?: Company
  total_assets: number
  high_confidence?: number
  medium_confidence?: number
  low_confidence?: number
  last_updated?: string
}

export type AppView = 'search' | 'processing' | 'results'
