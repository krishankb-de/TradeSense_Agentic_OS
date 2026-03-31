/**
 * Shared TypeScript types for TradeSense
 * These types mirror the Python Pydantic models for cross-language compatibility
 */

// ============================================================================
// Enums
// ============================================================================

export enum LeadSource {
  VOICE = "voice",
  SMS = "sms",
  WEB = "web",
}

export enum LeadStatus {
  NEW = "new",
  TRIAGED = "triaged",
  SCHEDULED = "scheduled",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
}

export enum Urgency {
  EMERGENCY = "emergency",
  URGENT = "urgent",
  ROUTINE = "routine",
}

export enum JobStatus {
  SCHEDULED = "scheduled",
  IN_PROGRESS = "in-progress",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
}

export enum PartSource {
  INVENTORY = "inventory",
  ORDERED = "ordered",
  CUSTOMER_SUPPLIED = "customer-supplied",
}

export enum Complexity {
  SIMPLE = "simple",
  MODERATE = "moderate",
  COMPLEX = "complex",
}

export enum Availability {
  IN_STOCK = "in-stock",
  ORDER_REQUIRED = "order-required",
  UNAVAILABLE = "unavailable",
}

export enum ComplianceStatus {
  COMPLIANT = "compliant",
  WARNING = "warning",
  NON_COMPLIANT = "non-compliant",
}

export enum UserRole {
  TECHNICIAN = "technician",
  CUSTOMER = "customer",
  DISPATCHER = "dispatcher",
  ADMIN = "admin",
}

// ============================================================================
// Base Types
// ============================================================================

export interface GeoLocation {
  latitude: number;
  longitude: number;
  address: string;
  city: string;
  state: string;
  zipCode: string;
}

export interface Part {
  id: string;
  name: string;
  manufacturer: string;
  modelNumber: string;
  quantity: number;
  unitCost: number;
  source: PartSource;
}

// ============================================================================
// Lead Types
// ============================================================================

export interface Lead {
  id: string;
  customerId: string;
  source: LeadSource;
  status: LeadStatus;
  issueDescription: string;
  urgency: Urgency;
  serviceType: string;
  location: GeoLocation;
  createdAt: Date;
  updatedAt: Date;
  assignedTechnicianId?: string;
  estimatedValue: number;
}

export interface TriageResult {
  serviceType: string;
  estimatedDuration: number;
  requiredSkills: string[];
  suggestedTechnicians: string[];
  priority: number;
  confidence: number;
}

// ============================================================================
// Job Types
// ============================================================================

export interface Diagnosis {
  issueType: string;
  rootCause: string;
  confidence: number;
  requiredParts: Part[];
  estimatedRepairTime: number;
  complexity: Complexity;
  reasoningSteps: string[];
}

export interface CarbonFootprint {
  totalEmissions: number;
  breakdown: Record<string, any>[];
  complianceStatus: ComplianceStatus;
  recommendations: string[];
  dataSources: string[];
}

export interface Job {
  id: string;
  leadId: string;
  technicianId: string;
  status: JobStatus;
  scheduledStart: Date;
  scheduledEnd: Date;
  actualStart?: Date;
  actualEnd?: Date;
  diagnosis?: Diagnosis;
  partsUsed: Part[];
  laborHours: number;
  totalCost: number;
  customerSignature?: string;
  photos: string[];
  notes: string;
  carbonFootprint?: CarbonFootprint;
}

// ============================================================================
// Conversation Types
// ============================================================================

export interface Intent {
  name: string;
  confidence: number;
  parameters: Record<string, any>;
}

export interface Entity {
  type: string;
  value: string;
  confidence: number;
  span: [number, number];
}

export interface ConversationTurn {
  speaker: string;
  content: string;
  timestamp: Date;
  agent?: string;
  actions: Record<string, any>[];
}

export interface ConversationContext {
  sessionId: string;
  userId: string;
  userRole: UserRole;
  currentIntent?: Intent;
  entities: Entity[];
  history: ConversationTurn[];
  state: Record<string, any>;
  metadata: Record<string, any>;
}

// ============================================================================
// MCP Types
// ============================================================================

export interface MCPError {
  code: number;
  message: string;
  data?: Record<string, any>;
}

export interface MCPToolCall {
  id: string;
  serverId: string;
  toolName: string;
  parameters: Record<string, any>;
  result?: any;
  error?: MCPError;
  timestamp: Date;
  duration: number;
  agentId: string;
}

// ============================================================================
// Parts and Inventory Types
// ============================================================================

export interface PartsRecommendation {
  primary: Part[];
  alternatives: Part[][];
  totalCost: number;
  availability: Availability;
  distributorOptions: Record<string, any>[];
}

export interface EquipmentInfo {
  manufacturer: string;
  model: string;
  serialNumber?: string;
  type: string;
  specifications: Record<string, any>;
}

// ============================================================================
// Schedule Types
// ============================================================================

export interface JobAssignment {
  jobId: string;
  technicianId: string;
  scheduledStart: Date;
  scheduledEnd: Date;
  estimatedTravelTime: number;
}

export interface Route {
  technicianId: string;
  assignments: JobAssignment[];
  totalDistance: number;
  totalDuration: number;
}

export interface Schedule {
  assignments: JobAssignment[];
  routes: Route[];
  estimatedCompletionTime: number;
  utilizationRate: number;
}
