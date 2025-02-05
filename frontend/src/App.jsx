import React, { useState } from 'react';
import GithubInput from './components/GithubInput';
import Result from './components/Result';
import { migrateCode } from './services/api';

function App() {
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleStartMigration = async (repoUrl) => {
        setLoading(true);
        setError(null);
        try {
            const data = await migrateCode(repoUrl);
            setResult(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mx-auto p-4 pt-6 md:p-6 lg:p-12 xl:p-24">
            <GithubInput onStartMigration={handleStartMigration} />
            <Result result={result} loading={loading} error={error} />
           
        </div>
    );
}

export default App;
