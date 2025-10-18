// src/pages/ReportsPage.jsx
import React from 'react';
import './ReportsPage.css';
import { mockReportData } from '../api/mockData';
import ReportStatCard from '../components/reports/ReportStatCard';
import ChartCard from '../components/reports/ChartCard';
import {
  FiFileText,
  FiCheckSquare,
  FiAlertTriangle,
  FiTruck,
  FiHome
} from 'react-icons/fi';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';

const ReportsPage = () => {
  const {
    summaryStats,
    documentsByMonth,
    documentTypes,
    assetDistribution,
    recentActivity
  } = mockReportData;

  const PIE_COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF'];

  return (
    <div className="reports-page">
      <header className="reports-header">
        <h1>Analytics Dashboard</h1>
        <p>An overview of your document management workflow.</p>
      </header>

      {/* Summary Stats */}
      <div className="stats-grid">
        <ReportStatCard title="Total Documents" value={summaryStats.totalDocuments} icon={<FiFileText />} />
        <ReportStatCard title="Processed" value={summaryStats.documentsProcessed} icon={<FiCheckSquare />} />
        <ReportStatCard title="Pending Review" value={summaryStats.pendingReview} icon={<FiAlertTriangle />} />
        <ReportStatCard title="Vehicles" value={summaryStats.totalVehicles} icon={<FiTruck />} />
        <ReportStatCard title="Buildings" value={summaryStats.totalBuildings} icon={<FiHome />} />
      </div>

      {/* Main Charts Row */}
      <div className="charts-row">
        <div className="main-chart">
          <ChartCard title="Document Processing Trends (Last 6 Months)">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={documentsByMonth}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="uploaded" stroke="#8884d8" activeDot={{ r: 8 }} />
                <Line type="monotone" dataKey="processed" stroke="#82ca9d" />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
        <div className="side-charts">
          <ChartCard title="Document Types">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={documentTypes} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {documentTypes.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
          <ChartCard title="Asset Distribution">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={assetDistribution} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                    <Cell fill="#0088FE" />
                    <Cell fill="#00C49F" />
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      </div>

      {/* Recent Activity Table */}
      <div className="activity-table">
        <ChartCard title="Recent Activity">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Description</th>
                <th>Timestamp</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentActivity.map(activity => (
                <tr key={activity.id}>
                  <td><span className={`badge badge-${activity.type.toLowerCase()}`}>{activity.type}</span></td>
                  <td>{activity.description}</td>
                  <td>{new Date(activity.timestamp).toLocaleString()}</td>
                  <td>{activity.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartCard>
      </div>
    </div>
  );
};

export default ReportsPage;