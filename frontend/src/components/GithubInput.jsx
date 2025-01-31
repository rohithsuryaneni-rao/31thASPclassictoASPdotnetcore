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
    <div className="flex-1 p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold text-center mb-6 text-gray-600">
        ASP Classic to ASP.NET Core Migration
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <textarea
            placeholder="Enter GitHub repository URL (e.g., https://github.com/username/repository)"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setError(""); // Clear error when input changes
            }}
            rows="2"
            className={`w-full p-4 border rounded-lg text-sm ${
              error ? "border-red-500" : "border-gray-300"
            }`}
            required
          />
          {error && (
            <p className="text-red-500 text-sm mt-1">
              Error: Failed to migrate the repository. Please check the URL and try again.
            </p>
          )}
        </div>
        <button
          type="submit"
          className="w-full py-2 px-4 text-white font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-600 transition-colors duration-300"
        >
          Start Migration
        </button>
      </form>
    </div>
  );
};

export default GithubInput;