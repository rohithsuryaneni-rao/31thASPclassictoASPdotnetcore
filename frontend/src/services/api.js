import axios from 'axios';

const API_URL = 'http://localhost:5000/convert';

export const migrateCode = async (url) => {
  try {
    const response = await axios.post(API_URL, { 
      repo_url: url 
    }, {
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      timeout: 120000  // Increased timeout to 2 minutes
    });
    return response.data.converted_files;
  } catch (error) {
    console.error("Migration Error:", error.response ? error.response.data : error.message);
    throw error;
  }
};