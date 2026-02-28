---
layout: default
title: Home
---

# Development Blog

Updates, architecture decisions, and community news from the Clawssistant project — an open-source, Claude AI-powered home assistant.

<ul class="post-list">
{% for post in site.posts %}
  <li>
    <span class="date">{{ post.date | date: "%b %d, %Y" }}</span>
    <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    {% if post.summary %}<p>{{ post.summary }}</p>{% endif %}
  </li>
{% endfor %}
</ul>

{% if site.posts.size == 0 %}
*No posts yet. The blog agent will publish the first post when development begins.*
{% endif %}
