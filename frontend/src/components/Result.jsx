
import React from 'react';

const Result = ({ result, loading, error }) => {
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
      {result && Object.keys(result).length > 0 ? (
        <div className="space-y-2">
          <h3 className="font-medium">Conversion Results:</h3>
          <ul className="list-disc list-inside text-sm">
            {Object.entries(result).map(([file, status]) => (
              <li key={file} className={status.includes('Error') ? 'text-red-600' : 'text-green-600'}>
                {file}: {status}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-gray-600">No files converted.</p>
      )}
    </div>
  );
};

export default Result;