// src/api/mockData.js

export const mockBuildings = [
  {
    id: 1,
    name: 'The Gandon Building',
    address: '15-19 Amiens St, Dublin 1',
    documents: [
      { id: 101, title: 'Land Registry Folio D12345F' },
      { id: 102, title: 'Original Deed of Conveyance (1998)' },
      { id: 103, title: 'Fire Safety Certificate (2022)' },
    ],
  },
  {
    id: 2,
    name: 'Clarence House',
    address: '7-11 Clarence St, Dublin 2',
    documents: [
      { id: 201, title: 'Property Title Deed (2005)' },
      { id: 202, title: 'Planning Permission Grant (2004)' },
    ],
  },
  {
    id: 3,
    name: 'The Gasworks',
    address: 'Barrow St, Dublin 4',
    documents: [
      { id: 301, title: 'Lease Agreement - TechCorp Inc.' },
      { id: 302, title: 'Building Energy Rating (BER) Certificate' },
      { id: 303, title: 'Structural Survey Report (2019)' },
      { id: 304, title: 'Certificate of Compliance' },
    ],
  },
  {
    id: 4,
    name: 'Heuston South Quarter',
    address: 'St. John\'s Road West, Dublin 8',
    documents: [
      { id: 401, title: 'Master Deed for Multi-Unit Development' },
      { id: 402, title: 'Deed of Transfer - Unit 5A' },
    ],
  },
  {
    id: 5,
    name: 'Spencer Dock',
    address: 'North Wall Quay, Dublin 1',
    documents: [
      { id: 501, title: 'Foreshore Licence Agreement' },
      { id: 502, title: 'Title Deeds for Block A' },
      { id: 503, title: 'Service Charge Agreement' },
    ],
  },
    {
    id: 6,
    name: 'Beacon Court',
    address: 'Sandyford, Dublin 18',
    documents: [
      { id: 601, title: 'Deed of Title' },
      { id: 602, title: 'Certificate of Title' },
    ],
  },
];
export const mockReportData = {
  summaryStats: {
    totalDocuments: 1450,
    documentsProcessed: 1390,
    pendingReview: 60,
    totalVehicles: 85,
    totalBuildings: 12,
  },
  documentsByMonth: [
    { name: 'Jan', processed: 80, uploaded: 100 },
    { name: 'Feb', processed: 120, uploaded: 130 },
    { name: 'Mar', processed: 150, uploaded: 160 },
    { name: 'Apr', processed: 180, uploaded: 190 },
    { name: 'May', processed: 220, uploaded: 230 },
    { name: 'Jun', processed: 250, uploaded: 260 },
  ],
  documentTypes: [
    { name: 'Invoices', value: 400 },
    { name: 'Lease Agreements', value: 300 },
    { name: 'Insurance', value: 300 },
    { name: 'NCT Certificates', value: 200 },
    { name: 'Other', value: 250 },
  ],
  assetDistribution: [
    { name: 'Vehicles', value: 1100 },
    { name: 'Buildings', value: 350 },
  ],
  recentActivity: [
    { id: 1, type: 'UPLOAD', description: 'Uploaded "Invoice_2023_01.pdf"', timestamp: '2023-06-15T10:30:00Z', status: 'Processed' },
    { id: 2, type: 'ASSIGN', description: 'Assigned "NCT_Cert_2024.pdf" to Vehicle 22-D-12345', timestamp: '2023-06-15T09:15:00Z', status: 'Completed' },
    { id: 3, type: 'REVIEW', description: 'Flagged "Lease_Agreement_Block_A.pdf" for review', timestamp: '2023-06-14T16:00:00Z', status: 'Pending' },
    { id: 4, type: 'UPLOAD', description: 'Uploaded "Building_Permit_001.pdf"', timestamp: '2023-06-14T14:20:00Z', status: 'Processed' },
    { id: 5, type: 'ASSIGN', description: 'Assigned "Property_Title_Deed.pdf" to The Gandon Building', timestamp: '2023-06-14T11:05:00Z', status: 'Completed' },
  ],
};