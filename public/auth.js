const authMessage = document.querySelector("#auth-message");
const loginForm = document.querySelector("#login-form");
const registerForm = document.querySelector("#register-form");

function showAuthMessage(text, type = "success") {
  authMessage.textContent = text;
  authMessage.className = `message ${type}`;
  authMessage.hidden = false;
}

async function requestAuth(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || "请求失败");
  }
  return result;
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = loginForm.querySelector(".submit-button");
    const payload = Object.fromEntries(new FormData(loginForm).entries());
    submitButton.disabled = true;
    submitButton.textContent = "登录中...";

    try {
      await requestAuth("/api/auth/login", payload);
      window.location.href = "/";
    } catch (error) {
      showAuthMessage(error.message, "error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "登录";
    }
  });
}

if (registerForm) {
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = registerForm.querySelector(".submit-button");
    const payload = Object.fromEntries(new FormData(registerForm).entries());
    submitButton.disabled = true;
    submitButton.textContent = "注册中...";

    try {
      await requestAuth("/api/auth/register", payload);
      window.location.href = "/";
    } catch (error) {
      showAuthMessage(error.message, "error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "注册并登录";
    }
  });
}
