import React, { useState } from "react";

const GithubInput = ({ onStartMigration }) => {
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");

  // Function to normalize GitHub URL
  const normalizeGithubUrl = (inputUrl) => {
    try {
      // Remove trailing slashes and whitespace
      let cleanUrl = inputUrl.trim().replace(/\/+$/, "");

      // Handle tree/blob/master/main paths
      cleanUrl = cleanUrl.replace(/\/(?:tree|blob)\/(?:master|main)\//, "/");

      // Extract the basic repository URL
      const urlPattern = /https:\/\/github\.com\/([^\/]+)\/([^\/]+)/;
      const match = cleanUrl.match(urlPattern);

      if (match) {
        // Return just the base repository URL
        return `https://github.com/${match[1]}/${match[2]}`;
      }

      throw new Error("Invalid GitHub URL format");
    } catch (err) {
      throw new Error("Please enter a valid GitHub repository URL");
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");

    try {
      const normalizedUrl = normalizeGithubUrl(url);
      onStartMigration(normalizedUrl);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="flex-1 p-8 bg-white rounded-lg shadow-xl max-w-md max-w-lg mx-auto">
      <h3 className="text-2xl font-semibold text-center mb-8 text-gray-700">
        ASP Classic to ASP.NET Core Migration
      </h3>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-3">
          <textarea
            placeholder="Enter GitHub repository URL (e.g., https://github.com/username/repository)"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setError(""); 
            }}
            rows="3"
            className={`w-full p-4 border rounded-lg text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-${error ? 'red-500' : 'teal-500'} transition duration-200 ease-in-out ${
              error ? "border-red-500" : "border-gray-300"
            }`}
            required
          />
          {error && (
            <p className="text-red-500 text-sm mt-2">
              Error: {error}
            </p>
          )}
        </div>
        <button
          type="submit"
          className="w-full py-3 px-6 text-white font-semibold rounded-lg bg-[#2e8b86] hover:bg-[#248d7c] hover:text-black transition-colors duration-300 ease-in-out shadow-md"
        >
          Start Migration
        </button>
      </form>
    </div>
  );
};

export default GithubInput;
