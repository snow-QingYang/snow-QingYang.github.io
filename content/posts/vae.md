---
title: Introduction to Variantional Autoencoder
date: 2023-12-20
tags: technical blog 
published: false
cover: images/murasame.webp
---
This is my first technical blog on my own website. 

A common VAE objective is

\[
\mathcal{L}(\theta,\phi;x)=\mathbb{E}_{q_\phi(z\mid x)}[\log p_\theta(x\mid z)]-D_{KL}(q_\phi(z\mid x)\|p(z)).
\]
