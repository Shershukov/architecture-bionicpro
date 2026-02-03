import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<any[]>([]);

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      setReportData(data);
      downloadAsFile(data);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Функция для скачивания файла
  const downloadAsFile = (data: any[]) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'prosthetics_report.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!initialized) {
    return <div>Loading Keycloak...</div>;
  }

  if (!keycloak.authenticated) {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
          <button
              onClick={() => keycloak.login()}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Login
          </button>
        </div>
    );
  }

  return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <div className="p-8 bg-white rounded-lg shadow-md w-full max-w-2xl">
          <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

          <button
              onClick={downloadReport}
              disabled={loading}
              className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
                  loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
          >
            {loading ? 'Generating Report...' : 'Download Report'}
          </button>

          {error && (
              <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
                {error}
              </div>
          )}
          {reportData.length > 0 && (
              <div className="mt-6 overflow-x-auto">
                <table className="min-w-full bg-white border">
                  <thead>
                  <tr>
                    <th className="py-2 px-4 border">User</th>
                    <th className="py-2 px-4 border">Steps</th>
                    <th className="py-2 px-4 border">Battery</th>
                    <th className="py-2 px-4 border">Model</th>
                  </tr>
                  </thead>
                  <tbody>
                  {reportData.map((item, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="py-2 px-4 border">{item.full_name}</td>
                        <td className="py-2 px-4 border">{item.total_steps}</td>
                        <td className="py-2 px-4 border">{item.avg_battery_level.toFixed(1)}%</td>
                        <td className="py-2 px-4 border">{item.model_name}</td>
                      </tr>
                  ))}
                  </tbody>
                </table>
              </div>
          )}
        </div>
      </div>
  );
};

export default ReportPage;