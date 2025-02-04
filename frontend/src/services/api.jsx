import React, { useState } from 'react';
import GithubInput from './components/GithubInput';
import Result from './components/Result';

function App() {
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const onStartMigration = async (repoUrl) => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('/convert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ repo_url: repoUrl })
            });
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            setResult(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container mx-auto p-4 pt-6 md:p-6 lg:p-12 xl:p-24">
            <GithubInput onStartMigration={onStartMigration} />
            <Result result={result} loading={loading} error={error} />
        </div>
    );
}

export default App;