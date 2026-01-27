export default async function handler(req, res) {
  const { videoId } = req.query;

  if (!videoId) {
    return res.status(400).json({ error: "Missing videoId" });
  }

  try {
    const response = await fetch(
      `https://youtubetranscript.p.rapidapi.com/?id=${videoId}`,
      {
        headers: {
          "X-RapidAPI-Key": process.env.RAPIDAPI_KEY,
          "X-RapidAPI-Host": "youtubetranscript.p.rapidapi.com"
        }
      }
    );

    const data = await response.json();

    const transcript = data
      .map(entry => entry.text)
      .join(" ");

    res.status(200).json({ transcript });
  } catch (err) {
    res.status(500).json({ error: "Failed to fetch captions" });
  }
}

