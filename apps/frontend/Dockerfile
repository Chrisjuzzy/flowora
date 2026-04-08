FROM node:20-alpine

WORKDIR /app

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_DEMO_AGENT_ID=1

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_DEMO_AGENT_ID=$NEXT_PUBLIC_DEMO_AGENT_ID

# Copy package files first for caching
COPY apps/frontend/package*.json ./

# Install dependencies
RUN npm install --force  # --force helps with some alpine issues

# Copy the rest of the code
COPY apps/frontend .

# Build the app
RUN npm run build

# Expose port (Next.js default)
EXPOSE 3000

# Run production server bound to all interfaces
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
CMD ["node", ".next/standalone/server.js"]
