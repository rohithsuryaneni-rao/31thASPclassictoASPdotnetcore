import React from 'react';
import { downloadProject } from '../services/api';

const Result = ({ result, loading, error }) => {
  const handleDownload = async (projectName) => {
    try {
      await downloadProject(projectName);
    } catch (err) {
      console.error('Download error:', err);
      // Optionally show an error message to the user
    }
  };

  if (loading) {
    return (
      <div className="flex-1 mt-8 p-4 bg-yellow-100 text-center text-gray-700 font-medium rounded-lg">
        Migrating... Please wait.
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 mt-8 p-4 bg-red-100 text-center text-red-700 font-medium rounded-lg">
        Error: {error}
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="flex-1 mt-8 p-6 bg-gray-50 border border-gray-300 rounded-lg shadow-lg">
      <h2 className="text-xl font-semibold mb-4">Converted Files</h2>
      {result && Object.keys(result.converted_files || {}).length > 0 ? (
        <>
          <div className="space-y-2">
            <h3 className="font-medium">Conversion Results:</h3>
            <ul className="list-disc list-inside text-sm">
              {Object.entries(result.converted_files || {}).map(([file, status]) => (
                <li key={file} className={status.includes('Error') ? 'text-red-600' : 'text-green-600'}>
                  {file}: {status}
                </li>
              ))}
            </ul>
          </div>
          {result.project_name && (
            <button
              onClick={() => handleDownload(result.project_name)}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              disabled={loading}
            >
              {loading ? 'Processing...' : 'Download Project Files'}
            </button>
          )}
        </>
      ) : (
        <p className="text-gray-600">No files converted.</p>
      )}
    </div>
  );
};

export default Result;