# 1. Build stage
FROM node:18-alpine AS builder

WORKDIR /frontend
#from dockercompose context is . so dockerfile seeing dockercompose path as root path.
COPY .env .env
# คัดลอกไฟล์ dependency ก่อนเพื่อ cache layer
COPY frontend/package.json frontend/package-lock.json* frontend/pnpm-lock.yaml* frontend/yarn.lock* ./
RUN \
  if [ -f frontend/package-lock.json ]; then npm ci; \
  elif [ -f frontend/pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install; \
  elif [ -f frontend/yarn.lock ]; then yarn install --frozen-lockfile; \
  else npm install; fi

# คัดลอก source code ที่เหลือ
COPY ./frontend .

# Build Next.js app
RUN npm run build

# 2. Production stage
FROM node:18-alpine AS runner

WORKDIR /app
COPY --from=builder /frontend/.env ./.env
ENV NODE_ENV=production

# คัดลอกไฟล์ที่จำเป็นจาก builder
COPY --from=builder /frontend/.next ./.next
COPY --from=builder /frontend/public ./public
COPY --from=builder /frontend/package.json ./package.json
COPY --from=builder /frontend/node_modules ./node_modules
COPY --from=builder /frontend/.env ./.env

EXPOSE 3000

CMD ["npm", "start"] 