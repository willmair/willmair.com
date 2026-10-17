/* willmair.com — small progressive enhancements. The site works without JavaScript except the contact form. */
(function () {
  "use strict";

  document.querySelectorAll("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* ---- Header: mobile menu + border once scrolled ---- */
  var header = document.querySelector(".site-header"), toggle = document.querySelector(".nav-toggle"), nav = document.querySelector(".nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }
  function onScroll() { if (header) header.classList.toggle("scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  /* ---- Reveal on scroll: hide only below-the-fold items, and show everything after 2.5 s regardless ---- */
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && reveals.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px" });
    reveals.forEach(function (el) {
      if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add("in"); else io.observe(el);
    });
    document.documentElement.classList.add("js-reveal");
    setTimeout(function () { reveals.forEach(function (el) { el.classList.add("in"); }); }, 2500);
  }

  /* ---- Media filter chips ---- */
  var chips = document.querySelectorAll(".chip[data-filter]");
  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      chips.forEach(function (o) { o.setAttribute("aria-pressed", o === c ? "true" : "false"); });
      var f = c.dataset.filter;
      document.querySelectorAll(".m-row").forEach(function (r) { r.hidden = f !== "all" && r.dataset.type !== f; });
    });
  });

  /* ---- Copy-to-clipboard for bios ---- */
  document.querySelectorAll(".copy-btn[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var src = document.getElementById(b.dataset.copy);
      if (!src || !navigator.clipboard) return;
      navigator.clipboard.writeText(src.innerText.trim()).then(function () {
        var old = b.textContent; b.textContent = "Copied"; setTimeout(function () { b.textContent = old; }, 1600);
      });
    });
  });

  /* ---- Contact form ----------------------------------------------------
     Delivered by Web3Forms (https://web3forms.com) to Will's Harvard inbox
     (recipient set in the Web3Forms dashboard). The sender name has no web
     address in it, so Harvard's spam filter doesn't flag it.             */
  var CONTACT_FORM_KEY = "fe2d9e97-2d71-44a4-8501-87e318278dcf";

  var form = document.getElementById("contact-form");
  if (form) {
    var TOPICS = { speaking: "Speaking invitation", media: "Media request", advising: "Advising or consulting", other: "Something else" };
    var HINTS = {
      "Speaking invitation": "Please include the event, date, location (or virtual), audience and format.",
      "Media request": "Please include your outlet, the topic and your deadline.",
      "Advising or consulting": "Please include your organization and a short description of what you have in mind.",
      "Something else": "For questions about joining or working with my lab, themairlab.com is the best place to start."
    };
    var topicSel = form.querySelector("#cf-topic"), hint = form.querySelector("#cf-hint"), status = form.querySelector("#cf-status");
    var wanted = TOPICS[new URLSearchParams(location.search).get("topic")];
    if (wanted) topicSel.value = wanted;
    function showHint() { hint.textContent = HINTS[topicSel.value] || ""; }
    topicSel.addEventListener("change", showHint); showHint();

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var d = Object.fromEntries(new FormData(form).entries());
      if (d.botcheck) return;
      if (!d.name || !d.email || !d.message || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email)) {
        status.className = "form-status err"; status.textContent = "Please add your name, a valid email and a message."; return;
      }
      var btn = form.querySelector("button[type=submit]"); btn.disabled = true;
      status.className = "form-status"; status.textContent = "Sending…";
      fetch("https://api.web3forms.com/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          access_key: CONTACT_FORM_KEY,
          subject: "Personal website – " + d.topic + " – " + d.name,
          from_name: "William Mair website",
          replyto: d.email,
          name: d.name, email: d.email, organization: d.organization || "", topic: d.topic,
          date_or_deadline: d.when || "", message: d.message
        })
      }).then(function (r) { return r.json(); }).then(function (res) {
        if (!res.success) throw new Error(res.message || "failed");
        form.reset(); showHint();
        status.className = "form-status ok"; status.textContent = "Thank you, your message has been sent. I’ll be in touch.";
      }).catch(function () {
        status.className = "form-status err"; status.textContent = "Sorry, something went wrong. Please try again in a moment.";
      }).then(function () { btn.disabled = false; });
    });
  }
})();
