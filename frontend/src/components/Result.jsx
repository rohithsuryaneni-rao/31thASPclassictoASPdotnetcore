import React, { useState, useEffect } from 'react';
import { downloadProject } from '../services/api';

const Result = ({ result, loading, error }) => {
  const [loadingFiles, setLoadingFiles] = useState([]);
  
  useEffect(() => {
    if (result && result.converted_files) {
      const files = Object.entries(result.converted_files || {});
      
      files.forEach((entry, index) => {
        setTimeout(() => {
          setLoadingFiles((prevFiles) => [...prevFiles, entry]);
        }, index * 1000); 
      });
    }
  }, [result]);

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
      <div className="flex-1 mt-8 max-w-lg p-6 bg-gray-100 text-center text-gray-700 font-medium rounded-lg shadow-md mx-auto">
        <span className="text-sm">Migrating Please wait...</span>
      </div>
    );
  }
  

  if (error) {
    return (
      <div className="flex-1 mt-8 p-6 bg-red-100 text-center text-red-700 font-medium rounded-lg shadow-md max-w-lg mx-auto">
        Error: {error}
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="flex-1 mt-8 p-8 bg-white border border-gray-300 rounded-lg shadow-xl max-w-lg mx-auto">
      <h2 className="text-2xl font-semibold mb-6 text-gray-700">Converted Files</h2>
      {result && Object.keys(result.converted_files || {}).length > 0 ? (
        <>
          <div className="space-y-4">
            <ul className="list-disc list-inside text-sm text-gray-600">
              {loadingFiles.map(([file, status], index) => (
                <li
                  key={file}
                  className={`${
                    status.includes('Error') ? 'text-red-600' : 'text-teal-600'
                  }`}
                >
                  {file}: {status} 
                  {index < loadingFiles.length - 1 && <span className="animate-pulse">...</span>}
                </li>
              ))}
              {/* Display a loading indicator while files are being processed */}
              {loadingFiles.length < (Object.entries(result.converted_files || {}).length) && (
                <li className="text-gray-500">Loading...</li>
              )}
            </ul>
          </div>
          {result.project_name && (
            <button
              onClick={() => handleDownload(result.project_name)}
              className="mt-6 px-6 py-3 bg-[#2e8b86] text-white rounded-lg hover:bg-[#248d7c] hover:text-black transition-colors duration-300 ease-in-out shadow-md"
              disabled={loading}
            >
              {loading ? 'Processing...' : 'Download Zip Files'}
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
