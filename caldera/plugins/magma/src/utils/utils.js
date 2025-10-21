export function getHumanFriendlyTime(date) {
  if (!date) return "";
  let split = date.split("-");

  let hMonth = Number(split[1]) - 1;
  let hDate = Number(split[2].split(" ")[0]);
  let hTime = split[2].split(" ")[1].split(":");

  const givenDate = Date.UTC(
    split[0],
    hMonth,
    hDate,
    hTime[0],
    hTime[1],
    hTime[2]
  );
  // Make a fuzzy time
  let delta = Math.round((Date.now() - givenDate) / 1000);

  let minute = 60,
    hour = minute * 60,
    day = hour * 24;

  let fuzzy;

  if (delta < 30) {
    fuzzy = "just now";
  } else if (delta < minute) {
    fuzzy = delta + " seconds ago";
  } else if (delta < 2 * minute) {
    fuzzy = "a minute ago";
  } else if (delta < hour) {
    fuzzy = Math.floor(delta / minute) + " min ago";
  } else if (Math.floor(delta / hour) === 1) {
    fuzzy = "1 hr ago";
  } else if (delta < day) {
    fuzzy = Math.floor(delta / hour) + " hrs ago";
  } else if (delta < day * 2) {
    fuzzy = "yesterday " + hTime.join(":");
  } else {
    switch (hMonth) {
      case 0:
        hMonth = "Jan";
        break;
      case 1:
        hMonth = "Feb";
        break;
      case 2:
        hMonth = "Mar";
        break;
      case 3:
        hMonth = "Apr";
        break;
      case 4:
        hMonth = "May";
        break;
      case 5:
        hMonth = "Jun";
        break;
      case 6:
        hMonth = "Jul";
        break;
      case 7:
        hMonth = "Aug";
        break;
      case 8:
        hMonth = "Sep";
        break;
      case 9:
        hMonth = "Oct";
        break;
      case 10:
        hMonth = "Nov";
        break;
      case 11:
        hMonth = "Dec";
        break;
      default:
        hMonth = "";
        break;
    }
    fuzzy = hMonth + " " + hDate + " " + hTime.join(":");
  }
  return fuzzy;
}

/**
 * Parse timestamp into human-friendly date ISO8601-safe format
 * @param dateTime {string} - Expected ISO8601 input in UTC time: (i.e.) 2021-08-25T10:03:23Z
 * @returns {string} - (i.e.) '5 hrs ago'
 */
export function getHumanFriendlyTimeISO8601(dateTime) {
  return getHumanFriendlyTime(dateTime.replace("T", " ").replace("Z", ""));
}

export function getReadableTime(date) {
  // i.e. format 2021-08-03 19:37:08
  if (!date) return "";
  date = date.replace("T", " ").replace("Z", "");
  let split = date.split("-");

  let hMonth = Number(split[1]) - 1;
  let hDate = Number(split[2].split(" ")[0]);
  let hTime = split[2].split(" ")[1].split(":");

  return new Date(
    Date.UTC(split[0], hMonth, hDate, hTime[0], hTime[1], hTime[2])
  ).toLocaleString("en-US", { timeZoneName: "short" });
}

export function b64DecodeUnicode(str) {
  //https://stackoverflow.com/a/30106551
  if (str != null) {
    // An error check is needed in case the wrong codec (i.e. not UTF-8) was used at source
    try {
      return decodeURIComponent(
        window
          .atob(str)
          .split("")
          .map(function (c) {
            return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
          })
          .join("")
      );
    } catch {
      return window.atob(str);
    }
  } else return "";
}

export function cartesian(args) {
  // Remove empty arrays from the input
  const filteredArgs = args.filter(arr => arr.length > 0);
  if (!filteredArgs.length) return [];
  let r = [], max = filteredArgs.length - 1;
  
  function helper(arr, i) {
      for (const element of filteredArgs[i]) {
          let a = arr.slice(0);
          a.push(element);
          (i === max) ? r.push(a) : helper(a, i + 1);
      }
  }
  
  helper([], 0);
  return r;
}