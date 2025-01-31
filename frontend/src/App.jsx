
import React, { useState } from 'react';
import GithubInput from './components/GithubInput';
import Result from './components/Result';
import { migrateCode } from './services/api';
import './style/App.css';

const App = () => {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleStartMigration = async (url) => {
    if (!url.trim()) {
      setError('Please enter a valid GitHub repository URL');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const convertedFiles = await migrateCode(url);
      setResult(convertedFiles);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || 'Failed to migrate the repository. Please check the URL and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="w-full max-w-6xl flex space-x-4">
        <GithubInput onStartMigration={handleStartMigration} />
        <Result result={result} loading={loading} error={error} />
      </div>
    </div>
  );
};

export default App;