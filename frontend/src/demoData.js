export const DEMO_JOB_DESCRIPTION = `Full Stack Developer — TechCorp

About the role
We are building a modern SaaS platform for HR teams.

Requirements
- 3+ years of experience with Python and FastAPI
- Strong knowledge of React and TypeScript
- Experience with PostgreSQL and Docker
- Familiarity with AWS and CI/CD pipelines
- Git workflow and agile methodologies

Nice to have
- Next.js, Redis, Kubernetes

What we offer
- Remote-friendly hybrid work
- Competitive salary and learning budget
`;

export const DEMO_CV = {
  document_language: "en",
  contact: {
    full_name: "Alex Developer",
    headline: "Software Engineer",
    email: "alex@example.com",
    phone: "+34 600 000 000",
    location: "Madrid, Spain",
    linkedin: "https://linkedin.com/in/alexdev",
    github: "https://github.com/alexdev",
    website: "",
  },
  summary:
    "Software engineer with 4 years building web applications. Focus on Python backends and React frontends.",
  skills: [
    "Python",
    "JavaScript",
    "React",
    "SQL",
    "Docker",
    "Git",
    "REST APIs",
  ],
  experience: [
    {
      role: "Backend Developer",
      company: "StartupXYZ",
      location: "Madrid",
      period: "2022 – Present",
      bullets: [
        "Built REST APIs with Python and FastAPI serving 50k daily requests.",
        "Designed PostgreSQL schemas and optimized slow queries by 40%.",
        "Deployed services with Docker on AWS EC2.",
      ],
    },
    {
      role: "Junior Developer",
      company: "WebAgency",
      location: "Remote",
      period: "2020 – 2022",
      bullets: [
        "Developed React dashboards for B2B clients.",
        "Collaborated in agile sprints with Git and code reviews.",
      ],
    },
  ],
  education: [
    {
      degree: "BSc Computer Science",
      school: "Universidad Complutense",
      period: "2016 – 2020",
    },
  ],
  languages: ["English: Advanced", "Spanish: Native"],
  certifications: [],
};

export function loadDemoData() {
  return {
    jobDescription: DEMO_JOB_DESCRIPTION,
    cv: DEMO_CV,
    filename: "demo-cv.json",
  };
}
