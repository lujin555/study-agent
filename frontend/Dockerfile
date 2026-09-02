# 前端镜像：多阶段构建 —— 先用 node 打包，再用 nginx 托管静态文件
FROM node:22-alpine AS build
WORKDIR /app
# 国内 npm 镜像加速
RUN npm config set registry https://registry.npmmirror.com
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
